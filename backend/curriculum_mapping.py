"""
Standard 2 (Program Design) — Curriculum Mapping.

Staff maintain a list of Program Intended Learning Outcomes (ILOs) and a
clean, de-duplicated course list (imported from an uploaded grades workbook
via course_matching.py, or entered manually), then mark which courses
address which ILOs. From that coverage matrix we compute:

- ILOs with zero/low coverage (too few courses address them)
- ILOs with heavy duplication (too many courses address them — possible
  curriculum redundancy)
- Courses with no mapped ILOs

Persistence: SQLite via db.py, same pattern as indicators.py.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

DEFAULT_LOW_COVERAGE_THRESHOLD = 2   # fewer than this many courses -> "low coverage"
DEFAULT_HEAVY_DUPLICATION_THRESHOLD = 6  # this many courses or more -> "heavy duplication"

_ILOS_TABLE = """
CREATE TABLE IF NOT EXISTS curriculum_ilos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ilo_code TEXT,
    ilo_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_COURSES_TABLE = """
CREATE TABLE IF NOT EXISTS curriculum_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL
)
"""

_MAP_TABLE = """
CREATE TABLE IF NOT EXISTS curriculum_course_ilo_map (
    course_id INTEGER NOT NULL REFERENCES curriculum_courses(id) ON DELETE CASCADE,
    ilo_id INTEGER NOT NULL REFERENCES curriculum_ilos(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (course_id, ilo_id)
)
"""


def init_db() -> None:
    init_schema(_ILOS_TABLE, _COURSES_TABLE, _MAP_TABLE)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


# ---------------------------------------------------------------------------
# ILOs CRUD
# ---------------------------------------------------------------------------

def list_ilos() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM curriculum_ilos ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def create_ilo(ilo_text: str, ilo_code: str | None = None) -> dict[str, Any]:
    if not ilo_text or not ilo_text.strip():
        raise ValueError("ilo_text is required")
    init_db()
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO curriculum_ilos (ilo_code, ilo_text, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (ilo_code, ilo_text.strip(), now, now),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM curriculum_ilos WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def update_ilo(ilo_id: int, ilo_text: str | None = None, ilo_code: str | None = None) -> dict[str, Any] | None:
    updates = {}
    if ilo_text is not None:
        if not ilo_text.strip():
            raise ValueError("ilo_text cannot be blank")
        updates["ilo_text"] = ilo_text.strip()
    if ilo_code is not None:
        updates["ilo_code"] = ilo_code
    if not updates:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM curriculum_ilos WHERE id = ?", (ilo_id,)).fetchone()
        return dict(row) if row else None

    init_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [_now_iso(), ilo_id]
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE curriculum_ilos SET {set_clause}, updated_at = ? WHERE id = ?", params)
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM curriculum_ilos WHERE id = ?", (ilo_id,)).fetchone()
    return dict(row)


def delete_ilo(ilo_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM curriculum_ilos WHERE id = ?", (ilo_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Courses CRUD + import (reuses course_matching.py normalization)
# ---------------------------------------------------------------------------

def list_courses() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM curriculum_courses ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def _find_existing_match(conn, candidate_name: str) -> dict[str, Any] | None:
    """Return an existing course row whose name auto-merges with candidate_name, if any."""
    from course_matching import compute_match_confidence, decide_match

    existing = conn.execute("SELECT * FROM curriculum_courses").fetchall()
    for row in existing:
        conf = compute_match_confidence(candidate_name, row["course_name"])
        if decide_match(conf).status == "auto_merge":
            return dict(row)
    return None


def create_course(course_name: str, source: str = "manual") -> dict[str, Any]:
    if not course_name or not course_name.strip():
        raise ValueError("course_name is required")
    course_name = course_name.strip()
    init_db()
    with get_connection() as conn:
        existing = _find_existing_match(conn, course_name)
        if existing is not None:
            return existing
        cur = conn.execute(
            "INSERT INTO curriculum_courses (course_name, source, created_at) VALUES (?, ?, ?)",
            (course_name, source, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM curriculum_courses WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def delete_course(course_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM curriculum_courses WHERE id = ?", (course_id,))
    return cur.rowcount > 0


def import_courses_bulk(course_names: list[str], source: str = "import") -> dict[str, Any]:
    """De-duplicate a raw list of course-name strings against course_matching,
    then insert only the ones not already covered by an existing course."""
    from course_matching import find_equivalent_courses

    clean_names = [n.strip() for n in course_names if n and n.strip()]
    clusters = find_equivalent_courses(clean_names, max_candidates=500)
    canonical_names = [cluster[0] for cluster in clusters]  # first member as canonical label

    added: list[dict[str, Any]] = []
    merged_into_existing: list[str] = []
    init_db()
    with get_connection() as conn:
        for name in canonical_names:
            existing = _find_existing_match(conn, name)
            if existing is not None:
                merged_into_existing.append(name)
                continue
            cur = conn.execute(
                "INSERT INTO curriculum_courses (course_name, source, created_at) VALUES (?, ?, ?)",
                (name, source, _now_iso()),
            )
            new_id = cur.lastrowid
            row = conn.execute("SELECT * FROM curriculum_courses WHERE id = ?", (new_id,)).fetchone()
            added.append(dict(row))

    return {
        "raw_count": len(clean_names),
        "clusters_found": len(clusters),
        "added": added,
        "merged_into_existing": merged_into_existing,
    }


def extract_course_names_from_excel(contents: bytes) -> list[str]:
    """Extract course names from an uploaded .xlsx using the same analytics
    pipeline that powers the main dashboard, so naming is consistent."""
    import io

    from academic_analytics import compute_academic_analytics
    from excel_reader import read_excel_adaptive

    dfs = read_excel_adaptive(io.BytesIO(contents))
    names: set[str] = set()
    for _sheet, df in dfs.items():
        try:
            academic = compute_academic_analytics(df, {})
        except Exception:
            logger.warning("compute_academic_analytics failed during course extraction", exc_info=True)
            continue
        for c in academic.get("all_courses", []) or []:
            name = c.get("course") or c.get("course_title")
            if name:
                names.add(str(name))
    return sorted(names)


# ---------------------------------------------------------------------------
# Coverage matrix
# ---------------------------------------------------------------------------

def set_mapping(course_id: int, ilo_id: int, mapped: bool) -> None:
    init_db()
    with get_connection() as conn:
        if mapped:
            conn.execute(
                "INSERT OR IGNORE INTO curriculum_course_ilo_map (course_id, ilo_id, created_at) VALUES (?, ?, ?)",
                (course_id, ilo_id, _now_iso()),
            )
        else:
            conn.execute(
                "DELETE FROM curriculum_course_ilo_map WHERE course_id = ? AND ilo_id = ?",
                (course_id, ilo_id),
            )


def get_matrix() -> dict[str, Any]:
    init_db()
    ilos = list_ilos()
    courses = list_courses()
    with get_connection() as conn:
        pairs = conn.execute("SELECT course_id, ilo_id FROM curriculum_course_ilo_map").fetchall()
    mapped_pairs = {(r["course_id"], r["ilo_id"]) for r in pairs}

    matrix: dict[int, dict[int, bool]] = {
        c["id"]: {i["id"]: (c["id"], i["id"]) in mapped_pairs for i in ilos} for c in courses
    }
    return {"ilos": ilos, "courses": courses, "matrix": matrix}


def compute_coverage_summary(
    low_threshold: int = DEFAULT_LOW_COVERAGE_THRESHOLD,
    dup_threshold: int = DEFAULT_HEAVY_DUPLICATION_THRESHOLD,
) -> dict[str, Any]:
    data = get_matrix()
    ilos = data["ilos"]
    courses = data["courses"]
    matrix = data["matrix"]

    ilo_coverage: dict[int, int] = {i["id"]: 0 for i in ilos}
    course_coverage: dict[int, int] = {c["id"]: 0 for c in courses}
    for course_id, ilo_map in matrix.items():
        for ilo_id, mapped in ilo_map.items():
            if mapped:
                ilo_coverage[ilo_id] += 1
                course_coverage[course_id] += 1

    ilos_by_id = {i["id"]: i for i in ilos}
    courses_by_id = {c["id"]: c for c in courses}

    zero_coverage_ilos = [ilos_by_id[iid] for iid, cnt in ilo_coverage.items() if cnt == 0]
    low_coverage_ilos = [ilos_by_id[iid] for iid, cnt in ilo_coverage.items() if 0 < cnt < low_threshold]
    heavy_duplication_ilos = [ilos_by_id[iid] for iid, cnt in ilo_coverage.items() if cnt >= dup_threshold]
    courses_without_ilos = [courses_by_id[cid] for cid, cnt in course_coverage.items() if cnt == 0]

    return {
        "total_ilos": len(ilos),
        "total_courses": len(courses),
        "ilo_coverage_counts": ilo_coverage,
        "course_coverage_counts": course_coverage,
        "zero_coverage_ilos": zero_coverage_ilos,
        "low_coverage_ilos": low_coverage_ilos,
        "heavy_duplication_ilos": heavy_duplication_ilos,
        "courses_without_ilos": courses_without_ilos,
    }


def get_export_data() -> dict[str, Any]:
    """Bundle the matrix + summary for docx export (curriculum_map_report.py)."""
    matrix_data = get_matrix()
    summary = compute_coverage_summary()
    return {**matrix_data, "summary": summary}
