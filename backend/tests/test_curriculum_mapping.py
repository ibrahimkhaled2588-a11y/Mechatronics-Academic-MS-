"""Smoke test for backend/curriculum_mapping.py (Standard 2 curriculum map).

Plain-script convention (see test_indicators.py / upload_test.py) — no
pytest in this repo's environment yet. Run directly:
`python tests/test_curriculum_mapping.py`.
Uses a throwaway SQLite file so it never touches real tracker data.
"""
import os
import sys
import tempfile

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

_tmp_db = os.path.join(tempfile.gettempdir(), "test_curriculum.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db

import curriculum_mapping as cm  # noqa: E402

# --- ILOs CRUD ---
ilo1 = cm.create_ilo("Apply mathematics and engineering fundamentals", "ILO1")
ilo2 = cm.create_ilo("Design a system to meet desired needs", "ILO2")
ilo3 = cm.create_ilo("Communicate effectively", "ILO3")
assert len(cm.list_ilos()) == 3

updated = cm.update_ilo(ilo1["id"], ilo_text="Apply math, science, and engineering fundamentals")
assert updated["ilo_text"] == "Apply math, science, and engineering fundamentals"

try:
    cm.create_ilo("   ")
    raise AssertionError("expected ValueError for blank ilo_text")
except ValueError:
    pass

# --- Courses CRUD + dedupe via course_matching ---
c1 = cm.create_course("BES 141 / Statics")
c2 = cm.create_course("MEC 305 / Control Systems")
assert len(cm.list_courses()) == 2

# A near-duplicate of an existing course should merge, not duplicate
dup = cm.create_course("bes 141 / statics")
assert dup["id"] == c1["id"], "near-duplicate course name should merge into the existing row"
assert len(cm.list_courses()) == 2

# --- bulk import dedupe ---
result = cm.import_courses_bulk([
    "BES 141 / Statics",       # matches c1, should be skipped
    "PRE 244 / Applied Mechanics(2)",
    "PRE 244 / Applied Mechanics (2)",  # near-duplicate of the previous -> one cluster
])
assert len(result["added"]) == 1, f"expected 1 new course from import, got {result['added']}"
assert len(cm.list_courses()) == 3

# --- mapping matrix ---
courses = cm.list_courses()
c3 = next(c for c in courses if "Applied Mechanics" in c["course_name"])

cm.set_mapping(c1["id"], ilo1["id"], True)
cm.set_mapping(c1["id"], ilo2["id"], True)
cm.set_mapping(c2["id"], ilo1["id"], True)
# ilo3 intentionally left with zero coverage
# c3 intentionally left unmapped

matrix_data = cm.get_matrix()
assert matrix_data["matrix"][c1["id"]][ilo1["id"]] is True
assert matrix_data["matrix"][c3["id"]][ilo1["id"]] is False

# toggle off
cm.set_mapping(c1["id"], ilo2["id"], False)
matrix_data = cm.get_matrix()
assert matrix_data["matrix"][c1["id"]][ilo2["id"]] is False

# re-toggle on for the summary checks below
cm.set_mapping(c1["id"], ilo2["id"], True)

# --- coverage summary ---
summary = cm.compute_coverage_summary(low_threshold=2, dup_threshold=2)
zero_ids = {i["id"] for i in summary["zero_coverage_ilos"]}
assert ilo3["id"] in zero_ids, "ILO3 has no courses mapped to it"
low_ids = {i["id"] for i in summary["low_coverage_ilos"]}
assert ilo2["id"] in low_ids, "ILO2 has exactly 1 course, below the low_threshold=2"
dup_ids = {i["id"] for i in summary["heavy_duplication_ilos"]}
assert ilo1["id"] in dup_ids, "ILO1 has 2 courses, at the dup_threshold=2"
unmapped_course_ids = {c["id"] for c in summary["courses_without_ilos"]}
assert c3["id"] in unmapped_course_ids

# --- export data + docx build (smoke only) ---
export_data = cm.get_export_data()
assert "summary" in export_data and "matrix" in export_data

from curriculum_map_report import build_curriculum_map_docx  # noqa: E402
docx_bytes = build_curriculum_map_docx(export_data)
assert isinstance(docx_bytes, bytes) and len(docx_bytes) > 0

# --- delete ---
assert cm.delete_ilo(ilo3["id"]) is True
assert cm.delete_ilo(999999) is False
assert cm.delete_course(c3["id"]) is True

os.remove(_tmp_db)
print("All curriculum_mapping.py tests passed.")
