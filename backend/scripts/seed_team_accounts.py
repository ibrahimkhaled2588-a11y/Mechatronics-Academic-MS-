"""
One-time helper: creates one member account per standard (1-7) with freshly
generated passwords, printed once so you can hand them out to the team.

Usage (run once, after the app is deployed and ADMIN_USERNAME/ADMIN_PASSWORD
are set — see DEPLOYMENT.md):

    BASE_URL=https://your-app.fly.dev ADMIN_USERNAME=coordinator ADMIN_PASSWORD=... \
        python backend/scripts/seed_team_accounts.py

Safe to re-run: any username that already exists is skipped and reported,
never overwritten. Uses only the stdlib (urllib) — no new dependency, and
no direct database access, so it works the same way against a local dev
server or the real deployed URL.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

STANDARDS = {
    1: "Mission & Program Management",
    2: "Program Design",
    3: "Teaching, Learning & Assessment",
    4: "Students & Graduates",
    5: "Faculty & Supporting Staff",
    6: "Resources & Learning Facilities",
    7: "Quality Assurance & Program Evaluation",
}

# Avoid ambiguous characters (l/1/I, O/0) since real people will type these.
_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"


def gen_password(length: int = 12) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def request(method: str, path: str, body: dict | None = None, cookie: str | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req) as resp:
            set_cookie = resp.headers.get("Set-Cookie")
            return resp.status, json.loads(resp.read().decode("utf-8")), set_cookie
    except urllib.error.HTTPError as exc:
        detail = json.loads(exc.read().decode("utf-8"))
        return exc.code, detail, None


def main() -> None:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        print("Set ADMIN_USERNAME and ADMIN_PASSWORD (the same ones you used for")
        print("`fly secrets set` / your Render env vars) before running this.")
        sys.exit(1)

    status, body, set_cookie = request(
        "POST", "/api/auth/login", {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if status != 200:
        print(f"Could not log in as '{ADMIN_USERNAME}' at {BASE_URL}: {body}")
        sys.exit(1)
    cookie = set_cookie.split(";")[0] if set_cookie else None
    print(f"Logged in as admin '{ADMIN_USERNAME}' at {BASE_URL}.\n")

    created: list[tuple[str, str, int, str]] = []
    for n, name in STANDARDS.items():
        username = f"std{n}"
        password = gen_password()
        status, body, _ = request(
            "POST", "/api/auth/users",
            {"username": username, "password": password, "role": "member", "standard_number": n},
            cookie=cookie,
        )
        if status == 200:
            created.append((username, password, n, name))
            print(f"  created  {username:<10} standard {n} ({name})")
        elif status == 422 and "already taken" in str(body.get("detail", "")):
            print(f"  skipped  {username:<10} (already exists)")
        else:
            print(f"  FAILED   {username:<10} -> {body}")

    if created:
        print("\nSave these somewhere safe -- they are shown once and not recoverable later:\n")
        print(f"{'username':<10} {'password':<14} standard")
        for username, password, n, name in created:
            print(f"{username:<10} {password:<14} {n}: {name}")


if __name__ == "__main__":
    main()
