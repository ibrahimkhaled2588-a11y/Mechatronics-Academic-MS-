"""Smoke test for backend/resources.py (Standard 6 resources & facilities).

Plain-script convention (see test_indicators.py) — run directly:
`python tests/test_resources.py`. Uses a throwaway SQLite file so it
never touches real tracker data.
"""
import datetime
import os
import sys
import tempfile

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

_tmp_db = os.path.join(tempfile.gettempdir(), "test_resources.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db

import resources as res  # noqa: E402

today = datetime.date.today()
overdue_date = (today - datetime.timedelta(days=5)).isoformat()
due_soon_date = (today + datetime.timedelta(days=10)).isoformat()
far_future_date = (today + datetime.timedelta(days=200)).isoformat()

# --- equipment CRUD ---
e1 = res.create_equipment("CNC Machine", category="Manufacturing Lab", location="Lab 3", next_maintenance_date=overdue_date)
e2 = res.create_equipment("3D Printer", category="Design Lab", location="Lab 1", next_maintenance_date=due_soon_date)
e3 = res.create_equipment("Oscilloscope", category="Electronics Lab", location="Lab 2", next_maintenance_date=far_future_date)
e4 = res.create_equipment("Broken Robot Arm", status="out_of_service")
assert len(res.list_equipment()) == 4
assert len(res.list_equipment(status="out_of_service")) == 1

try:
    res.create_equipment("X", status="not_a_real_status")
    raise AssertionError("expected ValueError for invalid status")
except ValueError:
    pass

try:
    res.create_equipment("   ")
    raise AssertionError("expected ValueError for blank name")
except ValueError:
    pass

updated = res.update_equipment(e3["id"], status="needs_repair")
assert updated["status"] == "needs_repair"
assert res.update_equipment(999999, status="operational") is None

# --- maintenance due ---
due = res.maintenance_due(days_ahead=30)
due_ids = {d["id"] for d in due}
assert e1["id"] in due_ids, "overdue equipment must appear in the due list"
assert e2["id"] in due_ids, "equipment due within 30 days must appear"
assert e3["id"] not in due_ids, "equipment due in 200 days must not appear in a 30-day window"
overdue_entry = next(d for d in due if d["id"] == e1["id"])
assert overdue_entry["overdue"] is True
due_soon_entry = next(d for d in due if d["id"] == e2["id"])
assert due_soon_entry["overdue"] is False

assert res.delete_equipment(e4["id"]) is True
assert res.delete_equipment(999999) is False
assert len(res.list_equipment()) == 3

# --- library holdings ---
res.create_library_holding("Mechatronics textbooks", subject_area="Mechatronics", count=40)
res.create_library_holding("IEEE journal access", subject_area="Electronics", count=1)
assert len(res.list_library_holdings()) == 2

try:
    res.create_library_holding("X", count=-5)
    raise AssertionError("expected ValueError for negative count")
except ValueError:
    pass

lib_id = res.list_library_holdings()[0]["id"]
assert res.delete_library_holding(lib_id) is True
assert len(res.list_library_holdings()) == 1

# --- budget ---
res.create_budget_entry("2025-2026", "Lab Equipment", 50000.0, notes="Annual allocation")
res.create_budget_entry("2025-2026", "Library", 10000.0)
res.create_budget_entry("2024-2025", "Lab Equipment", 45000.0)
assert len(res.list_budget_entries()) == 3
assert len(res.list_budget_entries(fiscal_year="2025-2026")) == 2

try:
    res.create_budget_entry("", "X", 100)
    raise AssertionError("expected ValueError for blank fiscal_year")
except ValueError:
    pass

budget_id = res.list_budget_entries(fiscal_year="2024-2025")[0]["id"]
assert res.delete_budget_entry(budget_id) is True
assert len(res.list_budget_entries()) == 2

# --- dashboard summary ---
summary = res.get_dashboard_summary()
assert summary["total_equipment"] == 3
assert summary["needs_repair_count"] == 1
assert summary["maintenance_due_count"] == 2
assert summary["total_library_titles"] == 1
assert summary["total_budget_amount"] == 60000.0

os.remove(_tmp_db)
print("All resources.py tests passed.")
