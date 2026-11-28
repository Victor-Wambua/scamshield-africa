"""Shared helpers for the seeded-server accessibility, keyboard, print and performance checks."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx
import pyotp
from conftest import APP_DIR, chrome_path  # noqa: F401

from scamshield.config import Settings
from scamshield.db import Database
from scamshield.seed import DEMO_PASSWORD, seed

SEED_PORT = 4303
SEED_BASE = f"http://127.0.0.1:{SEED_PORT}"
SEED_SECRET = "a11y-secret-key-not-for-production"
AXE = Path(__file__).parent / "vendor" / "axe.min.js"

ROLES = {
    "anon": None,
    "reporter": "reporter1@demo.example",
    "moderator": "moderator@demo.example",
    "analyst": "analyst@bank.demo.example",
    "org_admin": "orgadmin@bank.demo.example",
    "platform_admin": "admin@demo.example",
}


@contextmanager
def seeded_server() -> Iterator[dict]:  # type: ignore[type-arg]
    tmp = Path(tempfile.mkdtemp())
    db_url = f"sqlite:///{tmp}/a11y.db"
    env = {**os.environ, "SS_DATABASE_URL": db_url, "SS_STORAGE_DIR": str(tmp / "ev"), "SS_SECRET_KEY": SEED_SECRET, "SS_ENV": "development", "SS_API_RATE_PER_MINUTE": "1000"}
    subprocess.run([sys.executable, "-m", "scamshield", "migrate"], cwd=APP_DIR, env=env, check=True, capture_output=True)
    settings = Settings(database_url=db_url, secret_key=SEED_SECRET, storage_dir=tmp / "ev")
    db = Database(db_url)
    with db.factory() as s:
        creds = seed(s, settings, None)
        s.commit()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "--factory", "scamshield.main:app_factory", "--port", str(SEED_PORT), "--log-level", "warning"], cwd=APP_DIR, env=env)
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{SEED_BASE}/healthz", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise RuntimeError("server did not start")
        yield {"creds": creds, "db": db}
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def sign_in(page, email: str, creds: dict) -> None:  # type: ignore[no-untyped-def]
    page.goto("/login")
    page.fill("#email", email)
    page.fill("#password", DEMO_PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    secret = creds.get(f"totp:{email}")
    if secret:
        page.fill("#code", pyotp.TOTP(secret).now())
        page.get_by_role("button", name="Verify").click()
    page.wait_for_load_state()


def screens(role: str, ids: dict[str, int]) -> list[str]:
    pub = ["/", "/search?q=0700000001", "/search?q=nothing-reported-here", "/search", f"/i/{ids['ind']}", "/report", "/analyse", "/about", "/login", "/register", "/recover", "/lang/sw", f"/correct/{ids['ind']}"]
    if role == "anon":
        return pub
    if role == "reporter":
        return ["/", "/mine", "/notifications", "/settings", "/mfa/setup", "/report"]
    if role == "moderator":
        return ["/mod", "/mod/corrections", f"/mod/{ids['rep']}", "/audit?verify=1", "/settings"]
    if role in ("analyst", "org_admin"):
        base = ["/org", "/org?days=7", "/org/campaigns", "/org/reports", "/org/cases", "/org/exports", "/org/alerts", "/dev", "/dev/docs", "/dev/usage", "/docs"]
        return base + ([f"/org/cases/{ids['case']}"] if ids.get("case") else [])
    return ["/admin", "/admin/orgs", "/admin/roles", "/audit?verify=1", "/mod", "/mod/corrections"]
