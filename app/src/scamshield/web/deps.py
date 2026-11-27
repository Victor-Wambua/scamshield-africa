"""Per-request context: DB session, current user, CSRF, template rendering, permission checks."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession
from starlette.datastructures import FormData

from .. import accounts
from ..config import Settings
from ..i18n import pick_language, translate
from ..models import Indicator, Session, User
from ..permissions import can
from ..security import csrf_for, csrf_valid, device_bucket, token_id
from .icons import ICONS

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
SESSION_COOKIE = "ss_session"
ANON_COOKIE = "ss_anon"

NAV: dict[str, list[tuple[str, str, str]]] = {
    "public": [("/", "nav_check", "search"), ("/report", "nav_report", "flag"), ("/analyse", "nav_analyse", "spark")],
    "moderator": [("/mod", "Queue", "queue"), ("/mod/corrections", "Corrections", "flag"), ("/audit", "Audit log", "log"), ("/", "Check", "search"), ("/notifications", "Alerts", "bell")],
    "org": [("/org", "Dashboard", "chart"), ("/org/campaigns", "Campaigns", "spark"), ("/org/cases", "Cases", "case"), ("/org/exports", "Exports", "download"), ("/org/alerts", "Alert rules", "bell"), ("/dev", "Developer", "key"), ("/", "Check", "search")],
    "admin": [("/admin", "Users", "users"), ("/admin/orgs", "Organisations", "store"), ("/admin/roles", "Roles", "lock"), ("/audit", "Audit log", "log"), ("/mod", "Moderation", "queue"), ("/mod/corrections", "Corrections", "flag"), ("/", "Check", "search")],
}


class Ctx:
    def __init__(self, request: Request, db: DbSession) -> None:
        self.request = request
        self.db = db
        self.settings: Settings = request.app.state.settings
        self.session: Session | None = accounts.session_for(db, request.cookies.get(SESSION_COOKIE))
        self.user: User | None = self.session.user if self.session else None
        self.anon_id = request.cookies.get(ANON_COOKIE) or secrets.token_urlsafe(16)
        self.new_anon = ANON_COOKIE not in request.cookies
        self.flash: list[tuple[str, str]] = []

    # ---- identity ----
    @property
    def role(self) -> str | None:
        return self.user.role if self.user else None

    @property
    def mfa_ok(self) -> bool:
        return bool(self.session and self.session.mfa_passed)

    @property
    def lang(self) -> str:
        return pick_language(self.request.cookies.get("ss_lang"), self.user.language if self.user else None)

    @property
    def client_bucket(self) -> str:
        ip = self.request.client.host if self.request.client else "unknown"
        return device_bucket(self.settings.secret_key, ip, self.request.headers.get("user-agent", ""))

    @property
    def csrf_token(self) -> str:
        binding = self.session.id if self.session else self.anon_id
        return csrf_for(self.settings.secret_key, binding)

    def commit(self) -> None:
        self.db.commit()

    # ---- access control ----
    def need(self, permission: str) -> User:
        """Return the user if allowed, else raise an HTTPException handled by the app (redirect/403)."""
        if not self.user:
            raise HTTPException(status_code=401)
        if accounts.needs_mfa(self.settings, self.user) and not self.mfa_ok:
            raise HTTPException(status_code=307, headers={"Location": "/mfa"})
        if not can(self.user.role, permission):
            raise HTTPException(status_code=403)
        return self.user

    def need_login(self) -> User:
        if not self.user:
            raise HTTPException(status_code=401)
        if accounts.needs_mfa(self.settings, self.user) and not self.mfa_ok:
            raise HTTPException(status_code=307, headers={"Location": "/mfa"})
        return self.user

    # ---- forms ----
    async def form(self) -> FormData:
        form = await self.request.form(max_files=10, max_fields=60)
        supplied = form.get("csrf_token")
        binding = self.session.id if self.session else self.anon_id
        if not csrf_valid(self.settings.secret_key, binding, supplied if isinstance(supplied, str) else None):
            raise HTTPException(status_code=403, detail="csrf")
        return form

    # ---- responses ----
    def theme_lang(self) -> str:
        return self.lang

    def render(self, name: str, status: int = 200, /, **kw: Any) -> HTMLResponse:
        nav_key = "public"
        if self.user:
            r = self.user.role
            nav_key = "moderator" if r == "moderator" else "org" if r in ("org_analyst", "org_admin") else "admin" if r == "platform_admin" else "public"
        items = NAV[nav_key]
        if nav_key == "public" and self.user:
            items = items + [("/mine", "nav_mine", "list"), ("/notifications", "nav_alerts", "bell")]
        if nav_key == "public" and not self.user:
            items = items + [("/login", "nav_signin", "user")]
        lang = self.lang
        demo = bool(self.request.app.state.demo_flag())
        context: dict[str, Any] = {
            "request": self.request, "user": self.user, "role": self.role, "csrf": self.csrf_token, "nav": items,
            "staff": nav_key != "public", "lang": lang, "t": lambda k: translate(lang, k), "icons": ICONS,
            "path": self.request.url.path, "demo": demo, "flash": self.flash, "settings": self.settings,
        }
        context.update(kw)
        resp = TEMPLATES.TemplateResponse(self.request, name, context, status_code=status)
        self.attach_cookies(resp)
        return resp

    def attach_cookies(self, resp: Response) -> None:
        if self.new_anon:
            resp.set_cookie(ANON_COOKIE, self.anon_id, httponly=True, samesite="lax", secure=self.settings.cookie_secure, max_age=86400 * 30)

    def redirect(self, url: str, status: int = 303) -> RedirectResponse:
        resp = RedirectResponse(url, status_code=status)
        self.attach_cookies(resp)
        return resp

    def set_session_cookie(self, resp: Response, token: str) -> None:
        resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=self.settings.cookie_secure, max_age=self.settings.session_hours * 3600, path="/")


def count_synthetic(db: DbSession) -> int:
    return len(db.scalars(select(Indicator.id).where(Indicator.origin == "synthetic test data").limit(1)).all())


def token_of(request: Request) -> str:
    return token_id(request.cookies.get(SESSION_COOKIE, ""))
