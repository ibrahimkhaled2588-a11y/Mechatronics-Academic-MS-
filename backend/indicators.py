"""
Standard 7 (Quality Assurance & Program Evaluation) — Accreditation Indicators Tracker.

Every other accreditation-support module (curriculum mapping, governance,
faculty data, resources, alumni) registers its evidence here as it's built,
so this tracker is the integration point across all 7 NAQAAE-style standards.

Persistence: SQLite via db.py (see ARCHITECTURE.md for why this app moved
off pure in-memory storage for accreditation data).
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

VALID_STATUSES = ("missing", "partial", "complete")

STANDARDS: dict[int, str] = {
    1: "Mission & Program Management",
    2: "Program Design",
    3: "Teaching, Learning & Assessment",
    4: "Students & Graduates",
    5: "Faculty & Supporting Staff",
    6: "Resources & Learning Facilities",
    7: "Quality Assurance & Program Evaluation",
}

# Placeholder indicator wording only — to be replaced with the official
# NAQAAE indicator text. Kept generic on purpose (see prompt: "don't invent
# official wording").
_PLACEHOLDER_INDICATORS: dict[int, list[str]] = {
    1: [
        "[Placeholder] Documented program mission approved by the relevant council",
        "[Placeholder] Program management structure and responsibilities defined",
        "[Placeholder] Evidence of stakeholder participation in governance decisions",
    ],
    2: [
        "[Placeholder] Program Intended Learning Outcomes (ILOs) documented",
        "[Placeholder] Curriculum map showing course coverage of ILOs",
        "[Placeholder] Evidence of periodic curriculum review",
    ],
    3: [
        "[Placeholder] Assessment methods aligned with course ILOs",
        "[Placeholder] Evidence of teaching quality monitoring",
        "[Placeholder] Grade distribution and performance analytics reviewed periodically",
    ],
    4: [
        "[Placeholder] Student admission and progression records maintained",
        "[Placeholder] Graduate/alumni tracking and employment outcomes recorded",
        "[Placeholder] Student satisfaction survey results reviewed",
    ],
    5: [
        "[Placeholder] Faculty roster with qualifications and specialization on file",
        "[Placeholder] Teaching load balance monitored per semester",
        "[Placeholder] Faculty research/publication activity logged",
    ],
    6: [
        "[Placeholder] Lab/equipment inventory maintained with maintenance schedule",
        "[Placeholder] Library holdings relevant to the program documented",
        "[Placeholder] Annual budget allocation for the program recorded",
    ],
    7: [
        "[Placeholder] Internal quality assurance committee meets on a defined cycle",
        "[Placeholder] Self-study report process documented",
        "[Placeholder] Closing-the-loop actions tracked for identified weaknesses",
    ],
}

_INDICATORS_TABLE = """
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_number INTEGER NOT NULL CHECK (standard_number BETWEEN 1 AND 7),
    indicator_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'missing' CHECK (status IN ('missing', 'partial', 'complete')),
    responsible_person TEXT,
    evidence_link TEXT,
    due_date TEXT,
    last_updated TEXT NOT NULL
)
"""

_LOOP_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS closing_the_loop_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    weakness_identified TEXT NOT NULL,
    action_taken TEXT,
    entry_status TEXT,
    entry_date TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def init_db() -> None:
    init_schema(_INDICATORS_TABLE, _LOOP_LOG_TABLE)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def seed_defaults(force: bool = False) -> int:
    """Seed placeholder indicators per standard if the table is empty.

    Returns the number of rows inserted. Idempotent unless force=True.
    """
    init_db()
    with get_connection() as conn:
        if not force:
            count = conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
            if count > 0:
                return 0
        else:
            conn.execute("DELETE FROM closing_the_loop_log")
            conn.execute("DELETE FROM indicators")

        now = _now_iso()
        rows = [
            (standard_number, text, "missing", None, None, None, now)
            for standard_number, texts in _PLACEHOLDER_INDICATORS.items()
            for text in texts
        ]
        conn.executemany(
            """
            INSERT INTO indicators
                (standard_number, indicator_text, status, responsible_person, evidence_link, due_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)


def _row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    d["standard_name"] = STANDARDS.get(d["standard_number"], "Unknown")
    return d


def list_indicators(
    standard_number: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM indicators WHERE 1=1"
    params: list[Any] = []
    if standard_number is not None:
        query += " AND standard_number = ?"
        params.append(standard_number)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY standard_number, id"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_indicator(indicator_id: int) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM indicators WHERE id = ?", (indicator_id,)).fetchone()
        if row is None:
            return None
        result = _row_to_dict(row)
        log_rows = conn.execute(
            "SELECT * FROM closing_the_loop_log WHERE indicator_id = ? ORDER BY id",
            (indicator_id,),
        ).fetchall()
        result["closing_the_loop_log"] = [dict(r) for r in log_rows]
        return result


def create_indicator(
    standard_number: int,
    indicator_text: str,
    responsible_person: str | None = None,
    evidence_link: str | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    if standard_number not in STANDARDS:
        raise ValueError(f"standard_number must be 1-7, got {standard_number}")
    if not indicator_text or not indicator_text.strip():
        raise ValueError("indicator_text is required")
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO indicators
                (standard_number, indicator_text, status, responsible_person, evidence_link, due_date, last_updated)
            VALUES (?, ?, 'missing', ?, ?, ?, ?)
            """,
            (standard_number, indicator_text.strip(), responsible_person, evidence_link, due_date, _now_iso()),
        )
        new_id = cur.lastrowid
    return get_indicator(new_id)  # type: ignore[return-value]


def update_indicator(indicator_id: int, **fields: Any) -> dict[str, Any] | None:
    """Update any subset of status/responsible_person/evidence_link/due_date."""
    allowed = {"status", "responsible_person", "evidence_link", "due_date", "indicator_text"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}")
    if not updates:
        return get_indicator(indicator_id)

    init_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [_now_iso(), indicator_id]
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE indicators SET {set_clause}, last_updated = ? WHERE id = ?",
            params,
        )
        if cur.rowcount == 0:
            return None
    return get_indicator(indicator_id)


def add_log_entry(
    indicator_id: int,
    weakness_identified: str,
    action_taken: str | None = None,
    entry_status: str | None = None,
    entry_date: str | None = None,
) -> dict[str, Any] | None:
    """Append a closing-the-loop entry (append-only, never edited or deleted)."""
    if not weakness_identified or not weakness_identified.strip():
        raise ValueError("weakness_identified is required")
    init_db()
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM indicators WHERE id = ?", (indicator_id,)).fetchone()
        if exists is None:
            return None
        conn.execute(
            """
            INSERT INTO closing_the_loop_log
                (indicator_id, weakness_identified, action_taken, entry_status, entry_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                indicator_id,
                weakness_identified.strip(),
                action_taken,
                entry_status,
                entry_date or _now_iso(),
                _now_iso(),
            ),
        )
    return get_indicator(indicator_id)


@dataclass(frozen=True)
class StandardSummary:
    standard_number: int
    standard_name: str
    total: int
    missing: int
    partial: int
    complete: int


def summarize_by_standard() -> list[StandardSummary]:
    indicators = list_indicators()
    summaries: list[StandardSummary] = []
    for num, name in STANDARDS.items():
        subset = [i for i in indicators if i["standard_number"] == num]
        summaries.append(
            StandardSummary(
                standard_number=num,
                standard_name=name,
                total=len(subset),
                missing=sum(1 for i in subset if i["status"] == "missing"),
                partial=sum(1 for i in subset if i["status"] == "partial"),
                complete=sum(1 for i in subset if i["status"] == "complete"),
            )
        )
    return summaries
