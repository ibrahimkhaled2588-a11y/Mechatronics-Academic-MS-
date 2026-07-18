"""
One-off migration: swap the placeholder indicator text already sitting in
an existing database for the real official NAQAAE wording now in
indicators.py's _SEED_INDICATORS. Never run automatically on startup —
this can delete data, so it's invoked by hand, once.

Usage (local dev, or anywhere you can set ACCREDITATION_DB_PATH to point
at the target database file directly):

    python backend/scripts/migrate_to_real_indicators.py

Against a deployed instance (Fly), SSH in first so this runs with access
to the actual mounted volume, then run the same command:

    fly ssh console -C "python backend/scripts/migrate_to_real_indicators.py"

What it does:
  - Inspects every existing indicator row. If NONE of them have any real
    work logged against them (status still "missing", no
    responsible_person/evidence_link/due_date, no closing-the-loop
    entries), it's safe to wipe the whole store and reseed from the new
    official list -- done automatically via indicators.seed_defaults(force=True).
  - If ANY indicator has real work logged, nothing is deleted. The 34
    official indicators are added as new rows (via create_indicator, same
    validation as the API), and every existing row's indicator_text is
    prefixed with "[Legacy Placeholder] " so it's still visible -- and
    anything already logged against it is preserved -- but clearly marked
    as superseded by the real indicator list.

Safe to re-run: seed_defaults() only seeds when the table is empty (unless
forced), and already-prefixed legacy rows won't be prefixed twice.
"""
from __future__ import annotations

import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

import indicators  # noqa: E402
from db import get_connection  # noqa: E402

_LEGACY_PREFIX = "[Legacy Placeholder] "


def _has_real_work_logged(rows: list[dict]) -> bool:
    for row in rows:
        if row["status"] != "missing":
            return True
        if row["responsible_person"] or row["evidence_link"] or row["due_date"]:
            return True
        if row.get("closing_the_loop_log"):
            return True
    return False


def main() -> None:
    indicators.init_db()
    existing = indicators.list_indicators()

    if not existing:
        print("No existing indicators found -- seeding the 34 official indicators fresh.")
        inserted = indicators.seed_defaults()
        print(f"Inserted {inserted} indicators.")
        return

    # list_indicators() doesn't include closing_the_loop_log; fetch each
    # row fully so the "any real work logged" check actually sees the log.
    full_rows = [indicators.get_indicator(r["id"]) for r in existing]

    if not _has_real_work_logged(full_rows):
        print(f"Found {len(existing)} existing indicators, none with real work logged "
              "(still 'missing' status, no responsible person/evidence/due date, no "
              "closing-the-loop entries) -- safe to wipe and reseed.")
        inserted = indicators.seed_defaults(force=True)
        print(f"Replaced with {inserted} official indicators.")
        return

    logged_count = sum(1 for r in full_rows if _has_real_work_logged([r]))
    print(f"Found {len(existing)} existing indicators, {logged_count} with real work "
          "already logged against them -- keeping all existing rows, not deleting anything.")

    with get_connection() as conn:
        already_prefixed = conn.execute(
            "SELECT COUNT(*) FROM indicators WHERE indicator_text LIKE ?",
            (_LEGACY_PREFIX + "%",),
        ).fetchone()[0]
        if already_prefixed == 0:
            conn.execute(
                "UPDATE indicators SET indicator_text = ? || indicator_text",
                (_LEGACY_PREFIX,),
            )
            print(f"Prefixed all {len(existing)} existing rows with '{_LEGACY_PREFIX.strip()}'.")
        else:
            print(f"{already_prefixed} rows already carry the legacy prefix -- skipping (already migrated).")

    current_texts_by_standard: dict[int, set[str]] = {}
    for row in indicators.list_indicators():
        current_texts_by_standard.setdefault(row["standard_number"], set()).add(row["indicator_text"])

    added = 0
    skipped = 0
    for standard_number, texts in indicators._SEED_INDICATORS.items():
        already_present = current_texts_by_standard.get(standard_number, set())
        for text in texts:
            if text in already_present:
                skipped += 1
                continue
            indicators.create_indicator(standard_number=standard_number, indicator_text=text)
            added += 1
    print(f"Added {added} official indicators alongside the {len(existing)} legacy rows"
          + (f" ({skipped} already present from a previous run, skipped)." if skipped else "."))
    print("Legacy rows are still visible in the tracker (prefixed), not deleted -- "
          "any status/evidence/closing-the-loop history already logged against them is intact.")


if __name__ == "__main__":
    main()
