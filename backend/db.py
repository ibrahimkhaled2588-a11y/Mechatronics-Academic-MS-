"""
Shared SQLite connection helper for accreditation-support data.

The rest of the app (upload analytics) stays in-memory/request-scoped by
design (see app.py `_upload_history`). Accreditation data — indicators,
ILOs, governance documents, faculty/resources/alumni registries — needs to
survive a server restart, so it lives in a single SQLite file. Each domain
module (indicators.py, curriculum_mapping.py, ...) owns its own tables and
calls `init_schema` with its own `CREATE TABLE IF NOT EXISTS` statements.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from config import get_server

_db_path = get_server().accreditation_db_path


def _ensure_parent_dir() -> None:
    parent = os.path.dirname(_db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with sane defaults; commits on success."""
    _ensure_parent_dir()
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema(*create_statements: str) -> None:
    """Run one or more idempotent CREATE TABLE IF NOT EXISTS statements."""
    with get_connection() as conn:
        for stmt in create_statements:
            conn.execute(stmt)
