from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pyotp
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from scamshield import accounts, security
from scamshield.config import Settings, set_settings
from scamshield.db import Database
from scamshield.main import create_app
from scamshield.models import Organisation, User
from scamshield.security import encrypt_field

PASSWORD = "Correct-Horse-9"


@pytest.fixture(scope="session", autouse=True)
def _fast_password_hashing() -> Iterator[None]:
    """Cheap Argon2 parameters in tests only (production parameters are covered by a dedicated test)."""
    real = security._ph
    security._ph = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    yield
    security._ph = real


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    s = Settings(
        database_url=f"sqlite:///{tmp_path}/test.db",
        secret_key="test-secret-key-not-for-production",
        storage_dir=tmp_path / "evidence",
        mail_log_path=tmp_path / "mail.log",
    )
    set_settings(s)
    return s


@pytest.fixture()
def database(settings: Settings) -> Database:
    d = Database(settings.database_url)
    d.create_all()
    return d


@pytest.fixture()
def app(settings: Settings, database: Database):  # type: ignore[no-untyped-def]
    return create_app(settings, database)


@pytest.fixture()
def db(database: Database) -> Iterator:  # type: ignore[type-arg]
    s = database.factory()
    yield s
    s.close()


@pytest.fixture()
def client(app) -> TestClient:  # type: ignore[no-untyped-def]
    return TestClient(app, base_url="http://testserver")


class Maker:
    def __init__(self, db, settings: Settings) -> None:  # type: ignore[no-untyped-def]
        self.db, self.settings, self.n = db, settings, 0

    def org(self, name: str | None = None) -> Organisation:
        self.n += 1
        o = Organisation(name=name or f"Org {self.n}", origin="synthetic test data")
        self.db.add(o)
        self.db.commit()
        return o

    def user(self, role: str = "reporter", org: Organisation | None = None, email: str | None = None) -> tuple[User, str | None]:
        self.n += 1
        u = accounts.register(self.db, email or f"u{self.n}@test.example", PASSWORD, f"User {self.n}", True, role=role, org_id=org.id if org else None, origin="synthetic test data")
        secret = None
        if role in self.settings.mfa_roles:
            secret = security.new_totp_secret()
            u.totp_secret_enc = encrypt_field(self.settings.secret_key, secret)
            u.totp_enabled = True
        self.db.commit()
        return u, secret


@pytest.fixture()
def make(db, settings: Settings) -> Maker:  # type: ignore[no-untyped-def]
    return Maker(db, settings)


def csrf_of(client: TestClient, path: str = "/") -> str:
    html = client.get(path).text
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', html)
    assert m, f"no csrf token on {path}"
    return m.group(1)


def login(app, user: User, secret: str | None = None, password: str = PASSWORD) -> TestClient:  # type: ignore[no-untyped-def]
    c = TestClient(app, base_url="http://testserver", follow_redirects=False)
    tok = csrf_of(c, "/login")
    r = c.post("/login", data={"email": user.email, "password": password, "csrf_token": tok})
    assert r.status_code == 303, r.text[:200]
    if secret:
        tok = csrf_of(c, "/mfa")
        r = c.post("/mfa", data={"code": pyotp.TOTP(secret).now(), "csrf_token": tok})
        assert r.status_code == 303, r.text[:200]
    return c


def post(c: TestClient, path: str, data: dict | None = None, form_path: str | None = None, **kw):  # type: ignore[no-untyped-def,type-arg]
    tok = csrf_of(c, form_path or path)
    payload = dict(data or {})
    payload["csrf_token"] = tok
    return c.post(path, data=payload, **kw)
