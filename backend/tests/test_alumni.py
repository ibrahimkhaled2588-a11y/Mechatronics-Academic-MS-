"""Smoke test for backend/alumni.py (Standard 4 alumni registry).

Plain-script convention (see test_indicators.py) — run directly:
`python tests/test_alumni.py`. Uses a throwaway SQLite file so it never
touches real tracker data.
"""
import os
import sys
import tempfile

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

_tmp_db = os.path.join(tempfile.gettempdir(), "test_alumni.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db

import alumni  # noqa: E402

# --- CRUD ---
a1 = alumni.create_alumnus("Ahmed Ibrahim", student_id="2019001", graduation_year=2023, employer="Acme Robotics")
a2 = alumni.create_alumnus("Sara Mostafa", student_id="2019002", graduation_year=2023)
a3 = alumni.create_alumnus("Youssef Adel", student_id="2018010", graduation_year=2022, employer="Nile Motors")
assert len(alumni.list_alumni()) == 3
assert len(alumni.list_alumni(graduation_year=2023)) == 2
assert a1["surveyed_at"] is None

try:
    alumni.create_alumnus("   ")
    raise AssertionError("expected ValueError for blank name")
except ValueError:
    pass

updated = alumni.update_alumnus(a2["id"], employer="Delta Electronics", current_role="Field Engineer")
assert updated["employer"] == "Delta Electronics"
assert updated["current_role"] == "Field Engineer"
assert alumni.update_alumnus(999999, employer="X") is None

# --- survey participation flag (not row-level survey linkage — see module docstring) ---
marked = alumni.mark_surveyed(a1["id"])
assert marked["surveyed_at"] is not None
assert alumni.mark_surveyed(999999) is None

# --- summary ---
summary = alumni.get_registry_summary()
assert summary["total_alumni"] == 3
# employed: a1 (Acme Robotics), a2 (Delta Electronics after update), a3 (Nile Motors) = 3/3
assert summary["employment_rate"] == 100.0
# surveyed: only a1 = 1/3
assert summary["survey_participation_rate"] == round(1 / 3 * 100, 1)
assert summary["by_graduation_year"] == {2023: 2, 2022: 1}

# --- delete ---
assert alumni.delete_alumnus(a3["id"]) is True
assert alumni.delete_alumnus(999999) is False
assert len(alumni.list_alumni()) == 2

os.remove(_tmp_db)
print("All alumni.py tests passed.")
