"""Smoke test for backend/auth.py (team login for the indicators tracker).

Plain-script convention (see test_indicators.py) — run directly:
`python tests/test_auth.py`. Uses a throwaway SQLite file so it never
touches real tracker data.
"""
import os
import sys
import tempfile

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

_tmp_db = os.path.join(tempfile.gettempdir(), "test_auth.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db

import auth  # noqa: E402

# --- password hashing round-trip ---
admin = auth.create_user("coordinator", "correct horse battery", role="admin")
assert admin["role"] == "admin"
assert admin["standard_number"] is None
assert "password_hash" not in admin and "salt" not in admin, "public user dict must never leak hash/salt"

member1 = auth.create_user("std1_lead", "another-strong-pw", role="member", standard_number=1)
assert member1["standard_number"] == 1

# --- validation ---
try:
    auth.create_user("bad", "short", role="member", standard_number=1)
    raise AssertionError("expected ValueError for password < 8 chars")
except ValueError:
    pass

try:
    auth.create_user("bad2", "longenoughpw", role="member", standard_number=None)
    raise AssertionError("expected ValueError for member with no standard_number")
except ValueError:
    pass

try:
    auth.create_user("bad3", "longenoughpw", role="member", standard_number=9)
    raise AssertionError("expected ValueError for out-of-range standard_number")
except ValueError:
    pass

try:
    auth.create_user("std1_lead", "longenoughpw", role="member", standard_number=2)
    raise AssertionError("expected ValueError for duplicate username")
except ValueError:
    pass

# --- authenticate ---
assert auth.authenticate("std1_lead", "another-strong-pw") is not None
assert auth.authenticate("std1_lead", "wrong-password") is None
assert auth.authenticate("nonexistent-user", "whatever1") is None

# --- sessions ---
token = auth.create_session(member1["id"])
session_user = auth.get_session_user(token)
assert session_user is not None
assert session_user["username"] == "std1_lead"
assert auth.get_session_user("not-a-real-token") is None
assert auth.get_session_user(None) is None

auth.delete_session(token)
assert auth.get_session_user(token) is None, "session must be invalidated after logout"

# --- can_edit_standard ---
assert auth.can_edit_standard(admin, 1) is True
assert auth.can_edit_standard(admin, 7) is True
assert auth.can_edit_standard(member1, 1) is True
assert auth.can_edit_standard(member1, 2) is False

# --- bootstrap_admin: no-op once an admin exists ---
os.environ["ADMIN_USERNAME"] = "should_not_be_created"
os.environ["ADMIN_PASSWORD"] = "should_not_be_created_pw"
auth.bootstrap_admin()
usernames = {u["username"] for u in auth.list_users()}
assert "should_not_be_created" not in usernames, "bootstrap_admin must not create a second admin"
del os.environ["ADMIN_USERNAME"]
del os.environ["ADMIN_PASSWORD"]

# --- list / reset / delete ---
assert len(auth.list_users()) == 2
updated = auth.reset_password(member1["id"], "brand-new-password")
assert updated is not None
assert auth.authenticate("std1_lead", "brand-new-password") is not None
assert auth.authenticate("std1_lead", "another-strong-pw") is None, "old password must stop working"

assert auth.reset_password(999999, "brand-new-password") is None
assert auth.delete_user(member1["id"]) is True
assert auth.delete_user(999999) is False
assert len(auth.list_users()) == 1

os.remove(_tmp_db)

# --- bootstrap_admin: actually creates the account on a fresh DB (the real
# first-deploy scenario) when ADMIN_USERNAME/ADMIN_PASSWORD are set ---
import importlib  # noqa: E402
import config as _config_mod  # noqa: E402
import db as _db_mod  # noqa: E402

_tmp_db2 = os.path.join(tempfile.gettempdir(), "test_auth_bootstrap.db")
if os.path.exists(_tmp_db2):
    os.remove(_tmp_db2)
os.environ["ACCREDITATION_DB_PATH"] = _tmp_db2
os.environ["ADMIN_USERNAME"] = "coordinator"
os.environ["ADMIN_PASSWORD"] = "bootstrap-password-1"
# config.py and db.py both cache the db path in module-level variables read
# at import time, so all three need reloading in dependency order for the
# new ACCREDITATION_DB_PATH to actually take effect.
importlib.reload(_config_mod)
importlib.reload(_db_mod)
importlib.reload(auth)
auth.bootstrap_admin()
users = auth.list_users()
assert len(users) == 1
assert users[0]["username"] == "coordinator"
assert users[0]["role"] == "admin"
assert auth.authenticate("coordinator", "bootstrap-password-1") is not None

os.remove(_tmp_db2)
del os.environ["ADMIN_USERNAME"]
del os.environ["ADMIN_PASSWORD"]

print("All auth.py tests passed.")
