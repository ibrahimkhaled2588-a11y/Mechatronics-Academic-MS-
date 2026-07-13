"""Smoke test for backend/indicators.py (Standard 7 tracker).

No pytest in this repo's environment yet (see upload_test.py for the same
plain-script convention) — run directly: `python tests/test_indicators.py`.
Uses a throwaway SQLite file so it never touches real tracker data.
"""
import os
import sys
import tempfile

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

_tmp_db = os.path.join(tempfile.gettempdir(), "test_accreditation.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db

import indicators  # noqa: E402

# --- seed ---
inserted = indicators.seed_defaults()
assert inserted == 21, f"expected 21 seeded placeholder indicators (3 per standard x 7), got {inserted}"
assert indicators.seed_defaults() == 0, "seed_defaults should be a no-op once the table is populated"

# --- list / filter ---
all_rows = indicators.list_indicators()
assert len(all_rows) == 21
std2_rows = indicators.list_indicators(standard_number=2)
assert all(r["standard_number"] == 2 for r in std2_rows)
assert len(std2_rows) == 3
missing_rows = indicators.list_indicators(status="missing")
assert len(missing_rows) == 21, "all seeded rows start as 'missing'"

# --- create ---
created = indicators.create_indicator(
    standard_number=3,
    indicator_text="Custom indicator for Standard 3",
    responsible_person="QA Coordinator",
)
assert created["standard_number"] == 3
assert created["status"] == "missing"
assert created["standard_name"] == "Teaching, Learning & Assessment"

try:
    indicators.create_indicator(standard_number=9, indicator_text="bad standard")
    raise AssertionError("expected ValueError for out-of-range standard_number")
except ValueError:
    pass

# --- update ---
updated = indicators.update_indicator(created["id"], status="partial", evidence_link="/exports/foo.docx")
assert updated["status"] == "partial"
assert updated["evidence_link"] == "/exports/foo.docx"

try:
    indicators.update_indicator(created["id"], status="not_a_real_status")
    raise AssertionError("expected ValueError for invalid status")
except ValueError:
    pass

assert indicators.update_indicator(999999, status="complete") is None, "updating a missing id should return None"

# --- closing-the-loop log ---
after_log = indicators.add_log_entry(
    created["id"],
    weakness_identified="No evidence uploaded yet",
    action_taken="Requested department chair to upload minutes",
    entry_status="in_progress",
)
assert len(after_log["closing_the_loop_log"]) == 1
entry = after_log["closing_the_loop_log"][0]
assert entry["weakness_identified"] == "No evidence uploaded yet"
assert entry["action_taken"] == "Requested department chair to upload minutes"

assert indicators.add_log_entry(999999, weakness_identified="x") is None

try:
    indicators.add_log_entry(created["id"], weakness_identified="   ")
    raise AssertionError("expected ValueError for blank weakness_identified")
except ValueError:
    pass

# --- summary ---
summary = indicators.summarize_by_standard()
assert len(summary) == 7
std3 = next(s for s in summary if s.standard_number == 3)
assert std3.total == 4, "3 seeded + 1 custom for Standard 3"
assert std3.partial == 1

# --- get_indicator round-trip ---
fetched = indicators.get_indicator(created["id"])
assert fetched["id"] == created["id"]
assert len(fetched["closing_the_loop_log"]) == 1

os.remove(_tmp_db)
print("All indicators.py tests passed.")
