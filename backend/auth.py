"""
Team login for the Standard 7 indicators tracker.

Seven team members each own one standard (1-7) and can only edit
indicators/log entries under their own standard; the admin (coordinator)
can see and edit everything, and manages the 7 accounts.

No new dependencies: passwords are hashed with stdlib pbkdf2_hmac (salted,
260k iterations — matches Django's current default), and sessions are
opaque random tokens (secrets.token_urlsafe) stored server-side, hashed
the same way passwords are so a stolen database dump doesn't hand over
live sessions. Sent to the browser as an httpOnly cookie.

The same login also gates the rest of the app now: governance (standard
1), curriculum mapping (standard 2), faculty (standard 5), and resources
(standard 6) each require their owning standard's lead (or an admin) via
require_standard_lead() in app.py — mirroring STANDARD_OWN_PAGE in
access_control.js so API access matches page access. Alumni is used from
the shared survey-dashboard page rather than a standard-specific one, so
it only requires login, same as the other shared pages.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import logging
import os
import secrets
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

VALID_ROLES = ("admin", "member")
SESSION_LIFETIME_DAYS = 14
_PBKDF2_ITERATIONS = 260_000

_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
    standard_number INTEGER CHECK (standard_number IS NULL OR (standard_number BETWEEN 1 AND 7)),
    created_at TEXT NOT NULL
)
"""

_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
)
"""


def init_db() -> None:
    init_schema(_USERS_TABLE, _SESSIONS_TABLE)


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def _now_iso() -> str:
    return _now().isoformat()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _hash_secret(secret: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), bytes.fromhex(salt_hex), _PBKDF2_ITERATIONS
    ).hex()


def _new_salt() -> str:
    return secrets.token_hex(16)


def _hash_token(token: str) -> str:
    # Sessions don't need per-token salts (tokens are already high-entropy
    # random values, not human-chosen secrets) — a single fast hash is
    # enough to avoid storing raw tokens, and keeps lookups a simple query.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# User management (admin-only, enforced by the caller in app.py)
# ---------------------------------------------------------------------------

def create_user(username: str, password: str, role: str, standard_number: int | None = None) -> dict[str, Any]:
    if not username or not username.strip():
        raise ValueError("username is required")
    if not password or len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {VALID_ROLES}")
    if role == "member" and standard_number is None:
        raise ValueError("member accounts must have a standard_number (1-7)")
    if standard_number is not None and not (1 <= standard_number <= 7):
        raise ValueError("standard_number must be between 1 and 7")

    init_db()
    salt = _new_salt()
    password_hash = _hash_secret(password, salt)
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, salt, role, standard_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username.strip(), password_hash, salt, role, standard_number, _now_iso()),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise ValueError(f"username '{username}' is already taken") from exc
            raise
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (new_id,)).fetchone()
    return _public_user(row)


def _public_user(row) -> dict[str, Any]:
    d = dict(row)
    d.pop("password_hash", None)
    d.pop("salt", None)
    return d


def list_users() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY role DESC, standard_number").fetchall()
    return [_public_user(r) for r in rows]


def delete_user(user_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return cur.rowcount > 0


def reset_password(user_id: int, new_password: str) -> dict[str, Any] | None:
    if not new_password or len(new_password) < 8:
        raise ValueError("password must be at least 8 characters")
    init_db()
    salt = _new_salt()
    password_hash = _hash_secret(new_password, salt)
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (password_hash, salt, user_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row)


def bootstrap_admin() -> None:
    """Create the first admin account from env vars if no admin exists yet.
    Safe to call on every startup — it's a no-op once an admin exists."""
    init_db()
    with get_connection() as conn:
        existing = conn.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if existing:
        return

    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not username or not password:
        logger.warning(
            "No admin account exists and ADMIN_USERNAME/ADMIN_PASSWORD are not set — "
            "the indicators tracker login will have no admin until you set those env "
            "vars and restart, or create one via create_user() directly."
        )
        return
    try:
        create_user(username, password, role="admin")
        logger.info("Bootstrapped admin account '%s' from ADMIN_USERNAME/ADMIN_PASSWORD.", username)
    except ValueError as exc:
        logger.warning("Could not bootstrap admin account: %s", exc)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def authenticate(username: str, password: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    if row is None:
        return None
    expected = row["password_hash"]
    actual = _hash_secret(password, row["salt"])
    if not hmac.compare_digest(expected, actual):
        return None
    return _public_user(row)


def create_session(user_id: int) -> str:
    init_db()
    token = secrets.token_urlsafe(32)
    now = _now()
    expires = now + datetime.timedelta(days=SESSION_LIFETIME_DAYS)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (_hash_token(token), user_id, now.isoformat(), expires.isoformat()),
        )
    return token


def get_session_user(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (_hash_token(token), _now_iso()),
        ).fetchone()
    return _public_user(row) if row else None


def delete_session(token: str | None) -> None:
    if not token:
        return
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))


def can_edit_standard(user: dict[str, Any], standard_number: int) -> bool:
    if user["role"] == "admin":
        return True
    return user.get("standard_number") == standard_number
