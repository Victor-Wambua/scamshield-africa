"""Browser end-to-end tests. They start the real server on port 4301 against a temporary migrated database."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, sync_playwright

from scamshield import accounts, security
from scamshield.config import Settings
from scamshield.db import Database
from scamshield.models import Organisation
from scamshield.security import encrypt_field

APP_DIR = Path(__file__).resolve().parents[1]
PORT = 4301
BASE = f"http://127.0.0.1:{PORT}"
SECRET = "e2e-secret-key-not-for-production"
PASSWORD = "E2e-Password-123"


def chrome_path() -> str | None:
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    cache = Path.home() / "Library/Caches/ms-playwright"
    for d in sorted(cache.glob("chromium-*")):
        p = d / "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        if p.exists():
            return str(p)
    return None


@pytest.fixture(scope="session")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict]:  # type: ignore[type-arg]
    tmp = tmp_path_factory.mktemp("e2e")
    db_url = f"sqlite:///{tmp}/e2e.db"
    env = {**os.environ, "SS_DATABASE_URL": db_url, "SS_STORAGE_DIR": str(tmp / "ev"), "SS_SECRET_KEY": SECRET, "SS_ENV": "development", "SS_API_RATE_PER_MINUTE": "100"}
    subprocess.run([sys.executable, "-m", "scamshield", "migrate"], cwd=APP_DIR, env=env, check=True, capture_output=True)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "--factory", "scamshield.main:app_factory", "--port", str(PORT), "--log-level", "warning"], cwd=APP_DIR, env=env)
    for _ in range(100):
        try:
            if httpx.get(f"{BASE}/healthz", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("server did not start")
    settings = Settings(database_url=db_url, secret_key=SECRET, storage_dir=tmp / "ev")
    database = Database(db_url)
    yield {"settings": settings, "db": database, "tmp": tmp}
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome_path())
        yield b
        b.close()


class Staff:
    def __init__(self, server: dict) -> None:  # type: ignore[type-arg]
        self.server, self.n = server, 0

    def create(self, role: str, org_name: str | None = None) -> tuple[str, str | None]:
        self.n += 1
        email = f"{role}{self.n}-{int(time.time() * 1000) % 100000}@e2e.example"
        with self.server["db"].factory() as db:
            org = None
            if org_name:
                from sqlalchemy import select

                org = db.scalar(select(Organisation).where(Organisation.name == org_name)) or Organisation(name=org_name, origin="synthetic test data")
                db.add(org)
                db.flush()
            u = accounts.register(db, email, PASSWORD, role, True, role=role, org_id=org.id if org else None, origin="synthetic test data")
            secret = None
            if role in self.server["settings"].mfa_roles:
                secret = security.new_totp_secret()
                u.totp_secret_enc = encrypt_field(SECRET, secret)
                u.totp_enabled = True
            db.commit()
        return email, secret


@pytest.fixture()
def staff(server: dict) -> Staff:  # type: ignore[type-arg]
    return Staff(server)


@pytest.fixture()
def new_page(browser: Browser):  # type: ignore[no-untyped-def]
    contexts = []

    def make(ua: str | None = None, mobile: bool = False):  # type: ignore[no-untyped-def]
        ctx = browser.new_context(user_agent=ua or "e2e-default", viewport={"width": 390, "height": 844} if mobile else {"width": 1280, "height": 900}, base_url=BASE)
        contexts.append(ctx)
        page = ctx.new_page()
        page.errors = []  # type: ignore[attr-defined]
        page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)  # type: ignore[attr-defined]
        page.on("pageerror", lambda e: page.errors.append(str(e)))  # type: ignore[attr-defined]
        return page

    yield make
    for c in contexts:
        c.close()
