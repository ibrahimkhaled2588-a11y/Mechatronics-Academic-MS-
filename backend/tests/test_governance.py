"""Smoke test for backend/governance.py (Standard 1 governance registers).

Plain-script convention (see test_indicators.py) — run directly:
`python tests/test_governance.py`. Uses a throwaway SQLite file and a
throwaway document storage directory so it never touches real data.
"""
import os
import shutil
import sys
import tempfile

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

_tmp_db = os.path.join(tempfile.gettempdir(), "test_governance.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db

_tmp_docs_dir = os.path.join(tempfile.gettempdir(), "test_governance_docs")
shutil.rmtree(_tmp_docs_dir, ignore_errors=True)

import governance as gov  # noqa: E402

# --- mission versions ---
assert gov.get_current_mission() is None
v1 = gov.create_mission_version("Prepare graduates for mechatronics engineering practice.")
v2 = gov.create_mission_version("Prepare graduates for mechatronics engineering practice and research.")
versions = gov.list_mission_versions()
assert len(versions) == 2
assert versions[0]["id"] == v2["id"], "list should be newest-first"
current = gov.get_current_mission()
assert current["id"] == v2["id"]
assert v1["id"] != v2["id"], "each save must create a new row, not overwrite"

try:
    gov.create_mission_version("   ")
    raise AssertionError("expected ValueError for blank mission_text")
except ValueError:
    pass

# --- document register ---
doc1 = gov.create_document(
    title="Department Council Minutes - Jan 2026",
    file_bytes=b"fake docx bytes",
    original_filename="minutes_jan2026.docx",
    storage_dir=_tmp_docs_dir,
    committee_name="Department Council",
    document_date="2026-01-15",
)
assert doc1["stored_filename"] == f"doc_{doc1['id']}.docx"
stored_path = os.path.join(_tmp_docs_dir, doc1["stored_filename"])
assert os.path.isfile(stored_path)
with open(stored_path, "rb") as f:
    assert f.read() == b"fake docx bytes"

doc2 = gov.create_document(
    title="QA Committee Minutes - Feb 2026",
    file_bytes=b"more bytes",
    original_filename="minutes_feb2026.pdf",
    storage_dir=_tmp_docs_dir,
    committee_name="QA Committee",
)
assert len(gov.list_documents()) == 2
assert len(gov.list_documents(committee_name="Department Council")) == 1

try:
    gov.create_document(
        title="", file_bytes=b"x", original_filename="x.pdf", storage_dir=_tmp_docs_dir,
    )
    raise AssertionError("expected ValueError for blank title")
except ValueError:
    pass

fetched = gov.get_document(doc1["id"])
assert fetched["title"] == "Department Council Minutes - Jan 2026"
assert gov.get_document(999999) is None

assert gov.delete_document(doc1["id"], _tmp_docs_dir) is True
assert not os.path.isfile(stored_path), "deleting a document should remove its file"
assert gov.delete_document(999999, _tmp_docs_dir) is False
assert len(gov.list_documents()) == 1

# --- stakeholder log ---
gov.add_stakeholder_entry(
    stakeholder_name="Ahmed Ibrahim",
    consulted_on="2026-02-01",
    topic="Curriculum revision priorities",
    stakeholder_role="Alumni",
)
gov.add_stakeholder_entry(
    stakeholder_name="Acme Robotics Co.",
    consulted_on="2026-02-10",
    topic="Graduate employability skills gap",
    stakeholder_role="Employer",
)
log = gov.list_stakeholder_log()
assert len(log) == 2
assert log[0]["stakeholder_name"] == "Acme Robotics Co.", "list should be newest-first"

try:
    gov.add_stakeholder_entry(stakeholder_name="", consulted_on="2026-01-01", topic="x")
    raise AssertionError("expected ValueError for blank stakeholder_name")
except ValueError:
    pass

os.remove(_tmp_db)
shutil.rmtree(_tmp_docs_dir, ignore_errors=True)
print("All governance.py tests passed.")
