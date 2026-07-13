"""Smoke test for backend/faculty_data.py (Standard 5 faculty data).

Plain-script convention (see test_indicators.py) — run directly:
`python tests/test_faculty_data.py`. Uses a throwaway SQLite file so it
never touches real tracker data.
"""
import os
import sys
import tempfile

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

_tmp_db = os.path.join(tempfile.gettempdir(), "test_faculty.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db

import faculty_data as fd  # noqa: E402

# --- roster CRUD ---
a = fd.create_faculty("Dr. A", specialization="Control Systems and Automation", degree="PhD", rank="Professor")
b = fd.create_faculty("Dr. B", specialization="Thermodynamics", degree="PhD", rank="Associate Professor")
c = fd.create_faculty("Dr. C", specialization="Thermodynamics", degree="PhD", rank="Assistant Professor")
d = fd.create_faculty("Dr. D (overloaded)", specialization="Thermodynamics", degree="PhD", rank="Lecturer")
assert len(fd.list_faculty()) == 4

try:
    fd.create_faculty("   ")
    raise AssertionError("expected ValueError for blank name")
except ValueError:
    pass

# --- teaching load: engineered for a clear overload flag ---
# Fall 2025: three faculty at 4 hours, one at 24 hours -> z(24) ~= 1.73 (>= default 1.5 threshold)
fd.create_teaching_load(a["id"], "Fall 2025", "Control Systems", 4)
fd.create_teaching_load(b["id"], "Fall 2025", "Thermodynamics and Heat Transfer", 4)
fd.create_teaching_load(c["id"], "Fall 2025", "Thermodynamics and Heat Transfer", 4)
fd.create_teaching_load(d["id"], "Fall 2025", "Thermodynamics and Heat Transfer", 24)

try:
    fd.create_teaching_load(a["id"], "Fall 2025", "X", -3)
    raise AssertionError("expected ValueError for non-positive hours")
except ValueError:
    pass

try:
    fd.create_teaching_load(999999, "Fall 2025", "X", 3)
    raise AssertionError("expected ValueError for unknown faculty_id")
except ValueError:
    pass

summary = fd.load_summary()
assert len(summary) == 4
d_entry = next(e for e in summary if e["faculty_id"] == d["id"])
assert d_entry["total_hours"] == 24

imbalance = fd.flag_load_imbalance()
overloaded = [f for f in imbalance if f["flag"] == "overloaded"]
assert any(f["faculty_id"] == d["id"] for f in overloaded), f"expected Dr. D flagged overloaded, got {imbalance}"
assert all(f["faculty_id"] != a["id"] for f in imbalance), "Dr. A's load (4h) should not be flagged"

# --- specialization gap: Dr. A teaches Control Systems (matches spec) ---
# and also gets assigned a Thermodynamics course this semester (no overlap with "Control Systems and Automation")
fd.create_teaching_load(a["id"], "Spring 2026", "Thermodynamics and Heat Transfer", 3)
fd.create_teaching_load(b["id"], "Spring 2026", "Thermodynamics and Heat Transfer", 3)

gaps = fd.flag_specialization_gaps()
gap_courses_for_a = [g for g in gaps if g["faculty_id"] == a["id"]]
assert len(gap_courses_for_a) == 1, f"expected exactly 1 gap for Dr. A, got {gap_courses_for_a}"
assert gap_courses_for_a[0]["semester"] == "Spring 2026"
# Dr. A's Fall 2025 "Control Systems" course (matches specialization) must NOT be flagged
assert not any(g["course_name"] == "Control Systems" for g in gaps if g["faculty_id"] == a["id"])
# Dr. B teaching Thermodynamics with a Thermodynamics specialization must NOT be flagged
assert not any(g["faculty_id"] == b["id"] for g in gaps)

# --- publications ---
pub = fd.create_publication(a["id"], "Robust Control of Mechatronic Systems", venue="IEEE", year=2025, pub_type="journal")
assert pub["title"] == "Robust Control of Mechatronic Systems"
assert len(fd.list_publications()) == 1
pubs = fd.list_publications()
assert pubs[0]["faculty_name"] == "Dr. A"

try:
    fd.create_publication(a["id"], "   ")
    raise AssertionError("expected ValueError for blank title")
except ValueError:
    pass

# --- dashboard summary ---
dash = fd.get_dashboard_summary()
assert dash["total_faculty"] == 4
assert dash["specialization_gap_count"] >= 1
assert dash["overloaded_count"] >= 1

# --- delete ---
load_id = fd.list_teaching_load()[0]["id"]
assert fd.delete_teaching_load(load_id) is True
assert fd.delete_teaching_load(999999) is False
assert fd.delete_publication(pub["id"]) is True
assert fd.delete_faculty(d["id"]) is True
assert len(fd.list_faculty()) == 3

os.remove(_tmp_db)
print("All faculty_data.py tests passed.")
