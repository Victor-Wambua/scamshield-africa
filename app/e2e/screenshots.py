"""Capture screenshots of the REAL application (seeded synthetic data) into docs/screenshots/.

Usage: python e2e/screenshots.py   (starts its own server on port 4302)
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pyotp
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from conftest import chrome_path  # noqa: E402

from scamshield.config import Settings  # noqa: E402
from scamshield.db import Database  # noqa: E402
from scamshield.seed import DEMO_PASSWORD, seed  # noqa: E402

APP_DIR = Path(__file__).resolve().parents[1]
OUT = APP_DIR.parent / "docs" / "screenshots"
PORT = 4302
BASE = f"http://127.0.0.1:{PORT}"
SECRET = "screenshot-secret-key-not-for-production"


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    db_url = f"sqlite:///{tmp}/shots.db"
    env = {**os.environ, "SS_DATABASE_URL": db_url, "SS_STORAGE_DIR": str(tmp / "ev"), "SS_SECRET_KEY": SECRET}
    subprocess.run([sys.executable, "-m", "scamshield", "migrate"], cwd=APP_DIR, env=env, check=True, capture_output=True)
    settings = Settings(database_url=db_url, secret_key=SECRET, storage_dir=tmp / "ev")
    db = Database(db_url)
    with db.factory() as s:
        creds = seed(s, settings, None)
        s.commit()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "--factory", "scamshield.main:app_factory", "--port", str(PORT), "--log-level", "warning"], cwd=APP_DIR, env=env)
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{BASE}/healthz", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        OUT.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=chrome_path())
            plan = [
                ("home", None, "/"), ("results", None, "/search?q=0700000001"), ("indicator-verified", None, None), ("analyser", "analyse", None),
                ("report", None, "/report"), ("mod-queue", "moderator@demo.example", "/mod"), ("mod-review", "moderator@demo.example", "/mod/3"),
                ("mod-corrections", "moderator@demo.example", "/mod/corrections"), ("audit", "moderator@demo.example", "/audit?verify=1"),
                ("org-dashboard", "orgadmin@bank.demo.example", "/org"), ("org-cases", "orgadmin@bank.demo.example", "/org/cases"), ("dev-keys", "orgadmin@bank.demo.example", "/dev"),
                ("admin-users", "admin@demo.example", "/admin"), ("notifications", "reporter1@demo.example", "/notifications"), ("mine", "reporter1@demo.example", "/mine"),
            ]
            for scheme in ("light", "dark"):
                for device, vp in (("desktop", {"width": 1280, "height": 900}), ("mobile", {"width": 390, "height": 844})):
                    ctxs: dict[str | None, object] = {}
                    for name, who, path in plan:
                        key = who if who != "analyse" else None
                        if key not in ctxs:
                            c = browser.new_context(viewport=vp, color_scheme=scheme, base_url=BASE, user_agent=f"shots-{key}")
                            pg = c.new_page()
                            if key:
                                pg.goto("/login")
                                pg.fill("#email", key)
                                pg.fill("#password", DEMO_PASSWORD)
                                pg.get_by_role("button", name="Sign in").click()
                                secret = creds.get(f"totp:{key}")
                                if secret:
                                    pg.fill("#code", pyotp.TOTP(secret).now())
                                    pg.get_by_role("button", name="Verify").click()
                                pg.wait_for_load_state()
                            ctxs[key] = (c, pg)
                        c, pg = ctxs[key]  # type: ignore[misc]
                        if name == "indicator-verified":
                            pg.goto("/search?q=0700000001")
                            pg.locator("a.result").first.click()
                        elif name == "analyser":
                            pg.goto("/analyse")
                            pg.fill("#text", "URGENT: Your KCB account will be suspended. Confirm your PIN at http://kcb-secure-login.top now or face legal action.")
                            pg.get_by_role("button", name="Analyse").click()
                        else:
                            pg.goto(path)
                        pg.wait_for_load_state()
                        pg.screenshot(path=str(OUT / f"{name}-{device}-{scheme}.png"), full_page=True)
                    for c, _pg in ctxs.values():
                        c.close()  # type: ignore[attr-defined]
            browser.close()
        print("screenshots written to", OUT)
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
