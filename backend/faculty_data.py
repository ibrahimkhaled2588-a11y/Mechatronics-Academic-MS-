"""
Standard 5 (Faculty & Supporting Staff).

- Faculty roster: specialization, degree, rank.
- Teaching load per semester (course + hours per faculty member).
- Research/publication log.

Flags reuse the statistical pattern already established in quality.py:
- Load imbalance: same z-score approach as quality.anomaly_density, applied
  per-semester to each faculty member's total teaching hours, to flag
  over/under-loaded staff instead of outlier data cells.
- Specialization gaps: a course is flagged when none of its assigned
  instructors' specialization text shares a normalized token with the
  course name — reusing course_matching.normalize_course_text so course
  naming stays consistent with the rest of the app.

Persistence: SQLite via db.py, same pattern as indicators.py / governance.py.
"""
from __future__ import annotations

import datetime
import logging
import statistics
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

DEFAULT_LOAD_Z_THRESHOLD = 1.5  # smaller than quality.py's 3.0 default: faculty cohorts are small

_FACULTY_TABLE = """
CREATE TABLE IF NOT EXISTS faculty_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialization TEXT,
    degree TEXT,
    rank TEXT,
    created_at TEXT NOT NULL
)
"""

_LOAD_TABLE = """
CREATE TABLE IF NOT EXISTS faculty_teaching_load (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id INTEGER NOT NULL REFERENCES faculty_members(id) ON DELETE CASCADE,
    semester TEXT NOT NULL,
    course_name TEXT NOT NULL,
    hours REAL NOT NULL,
    created_at TEXT NOT NULL
)
"""

_PUBLICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS faculty_publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id INTEGER NOT NULL REFERENCES faculty_members(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    venue TEXT,
    year INTEGER,
    pub_type TEXT,
    created_at TEXT NOT NULL
)
"""


def init_db() -> None:
    init_schema(_FACULTY_TABLE, _LOAD_TABLE, _PUBLICATIONS_TABLE)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Faculty roster CRUD
# ---------------------------------------------------------------------------

def create_faculty(name: str, specialization: str | None = None, degree: str | None = None, rank: str | None = None) -> dict[str, Any]:
    if not name or not name.strip():
        raise ValueError("name is required")
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO faculty_members (name, specialization, degree, rank, created_at) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), specialization, degree, rank, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM faculty_members WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_faculty() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM faculty_members ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def delete_faculty(faculty_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM faculty_members WHERE id = ?", (faculty_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Teaching load CRUD
# ---------------------------------------------------------------------------

def create_teaching_load(faculty_id: int, semester: str, course_name: str, hours: float) -> dict[str, Any]:
    if not semester or not semester.strip():
        raise ValueError("semester is required")
    if not course_name or not course_name.strip():
        raise ValueError("course_name is required")
    try:
        hours = float(hours)
    except (TypeError, ValueError):
        raise ValueError("hours must be a number")
    if hours <= 0:
        raise ValueError("hours must be positive")

    init_db()
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM faculty_members WHERE id = ?", (faculty_id,)).fetchone()
        if exists is None:
            raise ValueError(f"faculty_id {faculty_id} does not exist")
        cur = conn.execute(
            "INSERT INTO faculty_teaching_load (faculty_id, semester, course_name, hours, created_at) VALUES (?, ?, ?, ?, ?)",
            (faculty_id, semester.strip(), course_name.strip(), hours, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM faculty_teaching_load WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_teaching_load(semester: str | None = None) -> list[dict[str, Any]]:
    init_db()
    query = """
        SELECT l.*, f.name AS faculty_name, f.specialization AS faculty_specialization
        FROM faculty_teaching_load l
        JOIN faculty_members f ON f.id = l.faculty_id
        WHERE 1=1
    """
    params: list[Any] = []
    if semester is not None:
        query += " AND l.semester = ?"
        params.append(semester)
    query += " ORDER BY l.semester, f.name"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def delete_teaching_load(load_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM faculty_teaching_load WHERE id = ?", (load_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Publications log
# ---------------------------------------------------------------------------

def create_publication(faculty_id: int, title: str, venue: str | None = None, year: int | None = None, pub_type: str | None = None) -> dict[str, Any]:
    if not title or not title.strip():
        raise ValueError("title is required")
    init_db()
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM faculty_members WHERE id = ?", (faculty_id,)).fetchone()
        if exists is None:
            raise ValueError(f"faculty_id {faculty_id} does not exist")
        cur = conn.execute(
            "INSERT INTO faculty_publications (faculty_id, title, venue, year, pub_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (faculty_id, title.strip(), venue, year, pub_type, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM faculty_publications WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_publications() -> list[dict[str, Any]]:
    init_db()
    query = """
        SELECT p.*, f.name AS faculty_name
        FROM faculty_publications p
        JOIN faculty_members f ON f.id = p.faculty_id
        ORDER BY p.year DESC, p.id DESC
    """
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def delete_publication(pub_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM faculty_publications WHERE id = ?", (pub_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Load summary + imbalance flags (z-score, same pattern as quality.py)
# ---------------------------------------------------------------------------

def load_summary() -> list[dict[str, Any]]:
    """Total teaching hours per faculty member per semester."""
    rows = list_teaching_load()
    totals: dict[tuple[int, str], dict[str, Any]] = {}
    for r in rows:
        key = (r["faculty_id"], r["semester"])
        entry = totals.setdefault(key, {
            "faculty_id": r["faculty_id"],
            "faculty_name": r["faculty_name"],
            "semester": r["semester"],
            "total_hours": 0.0,
            "course_count": 0,
        })
        entry["total_hours"] += r["hours"]
        entry["course_count"] += 1
    return sorted(totals.values(), key=lambda e: (e["semester"], e["faculty_name"]))


def flag_load_imbalance(z_threshold: float = DEFAULT_LOAD_Z_THRESHOLD) -> list[dict[str, Any]]:
    """Per-semester z-score flags for over/under-loaded faculty (same
    statistical pattern as quality.anomaly_density: z = (x - mean) / std)."""
    summary = load_summary()
    by_semester: dict[str, list[dict[str, Any]]] = {}
    for entry in summary:
        by_semester.setdefault(entry["semester"], []).append(entry)

    flags: list[dict[str, Any]] = []
    for semester, entries in by_semester.items():
        hours = [e["total_hours"] for e in entries]
        if len(hours) < 2:
            continue  # need at least 2 points for a meaningful std dev
        mean = statistics.fmean(hours)
        std = statistics.pstdev(hours)
        if std == 0:
            continue
        for e in entries:
            z = (e["total_hours"] - mean) / std
            if abs(z) >= z_threshold:
                flags.append({
                    **e,
                    "z_score": round(z, 2),
                    "flag": "overloaded" if z > 0 else "underloaded",
                })
    return sorted(flags, key=lambda f: (f["semester"], -abs(f["z_score"])))


# ---------------------------------------------------------------------------
# Specialization gap flags
# ---------------------------------------------------------------------------

_STOPWORDS = {"and", "of", "the", "in", "for", "to", "a", "an"}


def flag_specialization_gaps() -> list[dict[str, Any]]:
    """Teaching-load entries where the assigned instructor's specialization
    shares no normalized, non-stopword token with the course name."""
    from course_matching import normalize_course_text

    rows = list_teaching_load()
    gaps: list[dict[str, Any]] = []
    for r in rows:
        course_tokens = set(normalize_course_text(r["course_name"]).split()) - _STOPWORDS
        spec_tokens = set(normalize_course_text(r["faculty_specialization"] or "").split()) - _STOPWORDS
        if not spec_tokens or not (course_tokens & spec_tokens):
            gaps.append({
                "load_id": r["id"],
                "faculty_id": r["faculty_id"],
                "faculty_name": r["faculty_name"],
                "faculty_specialization": r["faculty_specialization"],
                "course_name": r["course_name"],
                "semester": r["semester"],
            })
    return gaps


def get_dashboard_summary(z_threshold: float = DEFAULT_LOAD_Z_THRESHOLD) -> dict[str, Any]:
    faculty = list_faculty()
    load = load_summary()
    imbalance = flag_load_imbalance(z_threshold)
    gaps = flag_specialization_gaps()
    avg_load = round(statistics.fmean([e["total_hours"] for e in load]), 2) if load else 0.0
    return {
        "total_faculty": len(faculty),
        "total_load_entries": len(load),
        "average_load_hours": avg_load,
        "overloaded_count": sum(1 for f in imbalance if f["flag"] == "overloaded"),
        "underloaded_count": sum(1 for f in imbalance if f["flag"] == "underloaded"),
        "specialization_gap_count": len(gaps),
        "load_imbalance_flags": imbalance,
        "specialization_gap_flags": gaps,
    }
