"""
Standard 1 (Mission & Program Management) — Governance.

Three simple registers, not analytics-heavy:

- Mission/goals text, versioned (every save adds a new version; nothing is
  overwritten, so the history of how the mission statement evolved is kept).
- A document register for council/committee minutes: the files themselves
  are stored on disk, only metadata (title, committee, date) is indexed
  in SQLite — same split as the survey-dashboard exports already do in
  app.py.
- An append-only stakeholder-participation log (who was consulted, when,
  on what).

Persistence: SQLite via db.py, same pattern as indicators.py / curriculum_mapping.py.
"""
from __future__ import annotations

import datetime
import logging
import os
import re
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

_MISSION_TABLE = """
CREATE TABLE IF NOT EXISTS governance_mission_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_text TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS governance_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    committee_name TEXT,
    document_date TEXT,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
)
"""

_STAKEHOLDER_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS governance_stakeholder_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stakeholder_name TEXT NOT NULL,
    stakeholder_role TEXT,
    consulted_on TEXT NOT NULL,
    topic TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL
)
"""


def init_db() -> None:
    init_schema(_MISSION_TABLE, _DOCUMENTS_TABLE, _STAKEHOLDER_LOG_TABLE)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Mission / goals — versioned, append-only
# ---------------------------------------------------------------------------

def create_mission_version(mission_text: str) -> dict[str, Any]:
    if not mission_text or not mission_text.strip():
        raise ValueError("mission_text is required")
    init_db()
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO governance_mission_versions (mission_text, created_at) VALUES (?, ?)",
            (mission_text.strip(), now),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM governance_mission_versions WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_mission_versions() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM governance_mission_versions ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_current_mission() -> dict[str, Any] | None:
    versions = list_mission_versions()
    return versions[0] if versions else None


# ---------------------------------------------------------------------------
# Document register — files on disk, metadata in SQLite
# ---------------------------------------------------------------------------

def _safe_stored_name(original_filename: str, doc_id: int) -> str:
    ext = os.path.splitext(original_filename)[1][:10]
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext) or ""
    return f"doc_{doc_id}{ext}"


def create_document(
    title: str,
    file_bytes: bytes,
    original_filename: str,
    storage_dir: str,
    committee_name: str | None = None,
    document_date: str | None = None,
) -> dict[str, Any]:
    if not title or not title.strip():
        raise ValueError("title is required")
    if not original_filename:
        raise ValueError("a file is required")
    init_db()
    os.makedirs(storage_dir, exist_ok=True)
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO governance_documents
                (title, committee_name, document_date, original_filename, stored_filename, uploaded_at)
            VALUES (?, ?, ?, ?, '', ?)
            """,
            (title.strip(), committee_name, document_date, original_filename, now),
        )
        new_id = cur.lastrowid
        stored_name = _safe_stored_name(original_filename, new_id)
        conn.execute(
            "UPDATE governance_documents SET stored_filename = ? WHERE id = ?",
            (stored_name, new_id),
        )
        row = conn.execute("SELECT * FROM governance_documents WHERE id = ?", (new_id,)).fetchone()

    with open(os.path.join(storage_dir, stored_name), "wb") as f:
        f.write(file_bytes)

    return dict(row)


def list_documents(committee_name: str | None = None) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM governance_documents WHERE 1=1"
    params: list[Any] = []
    if committee_name is not None:
        query += " AND committee_name = ?"
        params.append(committee_name)
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_document(doc_id: int) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM governance_documents WHERE id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def delete_document(doc_id: int, storage_dir: str) -> bool:
    init_db()
    doc = get_document(doc_id)
    if doc is None:
        return False
    with get_connection() as conn:
        conn.execute("DELETE FROM governance_documents WHERE id = ?", (doc_id,))
    file_path = os.path.join(storage_dir, doc["stored_filename"])
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            logger.warning("Could not remove governance document file %s", file_path, exc_info=True)
    return True


# ---------------------------------------------------------------------------
# Stakeholder participation log — append-only
# ---------------------------------------------------------------------------

def add_stakeholder_entry(
    stakeholder_name: str,
    consulted_on: str,
    topic: str,
    stakeholder_role: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if not stakeholder_name or not stakeholder_name.strip():
        raise ValueError("stakeholder_name is required")
    if not topic or not topic.strip():
        raise ValueError("topic is required")
    if not consulted_on or not consulted_on.strip():
        raise ValueError("consulted_on is required")
    init_db()
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO governance_stakeholder_log
                (stakeholder_name, stakeholder_role, consulted_on, topic, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (stakeholder_name.strip(), stakeholder_role, consulted_on.strip(), topic.strip(), notes, now),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM governance_stakeholder_log WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_stakeholder_log() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM governance_stakeholder_log ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]
