"""
Standard 4 (Students & Graduates) — Alumni Registry.

A named graduate roster (student ID, graduation year, current
employer/role) that lives alongside the existing survey dashboard rather
than duplicating any of its analysis logic (survey_dashboard.py stays
untouched).

Important constraint this design works around: survey_dashboard.py's
uploaded "graduates" survey responses are fully anonymous and aggregate
only (per-question percentage distributions — see analyze_question() /
calculate_satisfaction() in survey_dashboard.py). There is no per-response
identity to join against, so an alumnus can't be linked to *their own*
individual survey row. What we can do, and what "linkable to survey
responses" means here in practice, is record per-alumnus whether they
participated in a survey round (surveyed_at) and surface roster stats
(employment rate, participation rate) on the same survey-dashboard.html
page as the aggregate satisfaction results, so the coordinator sees both
pieces of Standard 4 evidence together.

Persistence: SQLite via db.py, same pattern as the other accreditation modules.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

_ALUMNI_TABLE = """
CREATE TABLE IF NOT EXISTS alumni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    name TEXT NOT NULL,
    graduation_year INTEGER,
    employer TEXT,
    current_role TEXT,
    contact_email TEXT,
    surveyed_at TEXT,
    created_at TEXT NOT NULL
)
"""


def init_db() -> None:
    init_schema(_ALUMNI_TABLE)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def create_alumnus(
    name: str,
    student_id: str | None = None,
    graduation_year: int | None = None,
    employer: str | None = None,
    current_role: str | None = None,
    contact_email: str | None = None,
) -> dict[str, Any]:
    if not name or not name.strip():
        raise ValueError("name is required")
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO alumni
                (student_id, name, graduation_year, employer, current_role, contact_email, surveyed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (student_id, name.strip(), graduation_year, employer, current_role, contact_email, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM alumni WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_alumni(graduation_year: int | None = None) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM alumni WHERE 1=1"
    params: list[Any] = []
    if graduation_year is not None:
        query += " AND graduation_year = ?"
        params.append(graduation_year)
    query += " ORDER BY graduation_year DESC, name"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def update_alumnus(alumnus_id: int, **fields: Any) -> dict[str, Any] | None:
    allowed = {"student_id", "name", "graduation_year", "employer", "current_role", "contact_email", "surveyed_at"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM alumni WHERE id = ?", (alumnus_id,)).fetchone()
        return dict(row) if row else None

    init_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [alumnus_id]
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE alumni SET {set_clause} WHERE id = ?", params)
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM alumni WHERE id = ?", (alumnus_id,)).fetchone()
    return dict(row)


def mark_surveyed(alumnus_id: int, surveyed_at: str | None = None) -> dict[str, Any] | None:
    return update_alumnus(alumnus_id, surveyed_at=surveyed_at or _now_iso())


def delete_alumnus(alumnus_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM alumni WHERE id = ?", (alumnus_id,))
    return cur.rowcount > 0


def get_registry_summary() -> dict[str, Any]:
    alumni = list_alumni()
    total = len(alumni)
    employed = sum(1 for a in alumni if a["employer"])
    surveyed = sum(1 for a in alumni if a["surveyed_at"])
    by_year: dict[int, int] = {}
    for a in alumni:
        if a["graduation_year"] is not None:
            by_year[a["graduation_year"]] = by_year.get(a["graduation_year"], 0) + 1
    return {
        "total_alumni": total,
        "employment_rate": round(employed / total * 100, 1) if total else 0.0,
        "survey_participation_rate": round(surveyed / total * 100, 1) if total else 0.0,
        "by_graduation_year": dict(sorted(by_year.items(), reverse=True)),
    }
