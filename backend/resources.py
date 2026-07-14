"""
Standard 6 (Resources & Learning Facilities).

- Lab/equipment inventory: status + next maintenance date.
- Library holdings: count per subject/category.
- Annual budget entries.

Simple registers plus one derived view (maintenance-due list) — not
analytics-heavy, matching resources.html's brief.

Persistence: SQLite via db.py, same pattern as the other accreditation modules.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

VALID_EQUIPMENT_STATUSES = ("operational", "needs_repair", "out_of_service")

_EQUIPMENT_TABLE = """
CREATE TABLE IF NOT EXISTS resources_equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'operational' CHECK (status IN ('operational', 'needs_repair', 'out_of_service')),
    next_maintenance_date TEXT,
    created_at TEXT NOT NULL
)
"""

_LIBRARY_TABLE = """
CREATE TABLE IF NOT EXISTS resources_library_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject_area TEXT,
    count INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
"""

_BUDGET_TABLE = """
CREATE TABLE IF NOT EXISTS resources_budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL
)
"""


def init_db() -> None:
    init_schema(_EQUIPMENT_TABLE, _LIBRARY_TABLE, _BUDGET_TABLE)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Equipment CRUD
# ---------------------------------------------------------------------------

def create_equipment(
    name: str,
    category: str | None = None,
    location: str | None = None,
    status: str = "operational",
    next_maintenance_date: str | None = None,
) -> dict[str, Any]:
    if not name or not name.strip():
        raise ValueError("name is required")
    if status not in VALID_EQUIPMENT_STATUSES:
        raise ValueError(f"status must be one of {VALID_EQUIPMENT_STATUSES}")
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO resources_equipment (name, category, location, status, next_maintenance_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name.strip(), category, location, status, next_maintenance_date, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM resources_equipment WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_equipment(status: str | None = None) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM resources_equipment WHERE 1=1"
    params: list[Any] = []
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def update_equipment(equipment_id: int, **fields: Any) -> dict[str, Any] | None:
    allowed = {"name", "category", "location", "status", "next_maintenance_date"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if "status" in updates and updates["status"] not in VALID_EQUIPMENT_STATUSES:
        raise ValueError(f"status must be one of {VALID_EQUIPMENT_STATUSES}")
    if not updates:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM resources_equipment WHERE id = ?", (equipment_id,)).fetchone()
        return dict(row) if row else None

    init_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [equipment_id]
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE resources_equipment SET {set_clause} WHERE id = ?", params)
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM resources_equipment WHERE id = ?", (equipment_id,)).fetchone()
    return dict(row)


def delete_equipment(equipment_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM resources_equipment WHERE id = ?", (equipment_id,))
    return cur.rowcount > 0


def maintenance_due(days_ahead: int = 30) -> list[dict[str, Any]]:
    """Equipment overdue or due for maintenance within `days_ahead` days."""
    cutoff = (datetime.date.today() + datetime.timedelta(days=days_ahead)).isoformat()
    today = datetime.date.today().isoformat()
    rows = list_equipment()
    due = [
        {**r, "overdue": r["next_maintenance_date"] < today}
        for r in rows
        if r["next_maintenance_date"] and r["next_maintenance_date"] <= cutoff
    ]
    return sorted(due, key=lambda r: r["next_maintenance_date"])


# ---------------------------------------------------------------------------
# Library holdings CRUD
# ---------------------------------------------------------------------------

def create_library_holding(title: str, count: int, subject_area: str | None = None) -> dict[str, Any]:
    if not title or not title.strip():
        raise ValueError("title is required")
    try:
        count = int(count)
    except (TypeError, ValueError):
        raise ValueError("count must be an integer")
    if count < 0:
        raise ValueError("count cannot be negative")
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO resources_library_holdings (title, subject_area, count, created_at) VALUES (?, ?, ?, ?)",
            (title.strip(), subject_area, count, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM resources_library_holdings WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_library_holdings() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM resources_library_holdings ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def delete_library_holding(holding_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM resources_library_holdings WHERE id = ?", (holding_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Budget entries CRUD
# ---------------------------------------------------------------------------

def create_budget_entry(fiscal_year: str, category: str, amount: float, notes: str | None = None) -> dict[str, Any]:
    if not fiscal_year or not fiscal_year.strip():
        raise ValueError("fiscal_year is required")
    if not category or not category.strip():
        raise ValueError("category is required")
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValueError("amount must be a number")
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO resources_budget (fiscal_year, category, amount, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (fiscal_year.strip(), category.strip(), amount, notes, _now_iso()),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM resources_budget WHERE id = ?", (new_id,)).fetchone()
    return dict(row)


def list_budget_entries(fiscal_year: str | None = None) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM resources_budget WHERE 1=1"
    params: list[Any] = []
    if fiscal_year is not None:
        query += " AND fiscal_year = ?"
        params.append(fiscal_year)
    query += " ORDER BY fiscal_year DESC, id"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def delete_budget_entry(entry_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM resources_budget WHERE id = ?", (entry_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

def get_dashboard_summary(maintenance_days_ahead: int = 30) -> dict[str, Any]:
    equipment = list_equipment()
    library = list_library_holdings()
    budget = list_budget_entries()
    due = maintenance_due(maintenance_days_ahead)
    return {
        "total_equipment": len(equipment),
        "needs_repair_count": sum(1 for e in equipment if e["status"] == "needs_repair"),
        "out_of_service_count": sum(1 for e in equipment if e["status"] == "out_of_service"),
        "maintenance_due_count": len(due),
        "maintenance_due": due,
        "total_library_titles": len(library),
        "total_library_items": sum(h["count"] for h in library),
        "total_budget_entries": len(budget),
        "total_budget_amount": round(sum(b["amount"] for b in budget), 2),
    }
