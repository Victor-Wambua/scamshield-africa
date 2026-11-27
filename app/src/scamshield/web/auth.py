"""Authentication, MFA, account pages (my reports, notifications, settings)."""

from __future__ import annotations

import io
import json
from typing import Any

import segno
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from starlette.datastructures import UploadFile

from .. import accounts, audit, ratelimit
from ..models import AlertSubscription, Evidence, Notification, NotificationPref, Report
from ..normalize import mask_value
from ..reports import recompute_indicator
from ..security import totp_uri
from ..uploads import UploadRejected, store_image
from .deps import SESSION_COOKIE, Ctx
from .guards import ctx_dep

router = APIRouter()
HOME = {"moderator": "/mod", "org_analyst": "/org", "org_admin": "/org", "platform_admin": "/admin"}
ALERT_CATEGORIES = ("reversal", "phishing", "investment", "jobs", "tax")


@router.get("/login", response_class=HTMLResponse)
def login_form(ctx: Ctx = Depends(ctx_dep)) -> Response:
    return ctx.render("login.html", errors={}, email="")


@router.post("/login", response_class=HTMLResponse)
async def login_submit(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    email, password = str(form.get("email") or ""), str(form.get("password") or "")
    rl = ratelimit.hit(ctx.db, f"login:{ctx.client_bucket}", ctx.settings.login_rate_per_15min, 900)
    if not rl.allowed:
        ctx.commit()
        return ctx.render("error.html", 429, title="Too many sign-in attempts", message="Please wait a few minutes and try again.")
    try:
        user = accounts.authenticate(ctx.db, ctx.settings, email, password)
    except accounts.LockedOut as exc:
        ctx.commit()
        return ctx.render("login.html", 429, errors={"form": str(exc)}, email=email)
    except accounts.LoginFailed as exc:
        ctx.commit()
        return ctx.render("login.html", 401, errors={"form": str(exc)}, email=email)
    if user.restricted and user.role == "reporter":
        pass  # restricted accounts may sign in (to read status) but cannot submit
    accounts.end_session(ctx.db, ctx.request.cookies.get(SESSION_COOKIE))
    token = accounts.create_session(ctx.db, ctx.settings, user)
    ctx.commit()
    dest = "/mfa" if accounts.needs_mfa(ctx.settings, user) else HOME.get(user.role, "/")
    resp = ctx.redirect(dest)
    ctx.set_session_cookie(resp, token)
    return resp


@router.post("/logout")
async def logout(ctx: Ctx = Depends(ctx_dep)) -> Response:
    await ctx.form()
    accounts.end_session(ctx.db, ctx.request.cookies.get(SESSION_COOKIE))
    ctx.commit()
    resp = ctx.redirect("/")
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_form(ctx: Ctx = Depends(ctx_dep)) -> Response:
    return ctx.render("register.html", errors={}, v={})


@router.post("/register", response_class=HTMLResponse)
async def register_submit(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    v = {k: str(form.get(k) or "") for k in ("email", "display_name")}
    rl = ratelimit.hit(ctx.db, f"register:{ctx.client_bucket}", 10, 3600)
    if not rl.allowed:
        ctx.commit()
        return ctx.render("error.html", 429, title="Too many sign-ups", message="Please try again later.")
    try:
        user = accounts.register(ctx.db, v["email"], str(form.get("password") or ""), v["display_name"], bool(form.get("terms")))
    except accounts.AccountError as exc:
        ctx.commit()
        return ctx.render("register.html", 422, errors=exc.errors, v=v)
    token = accounts.create_session(ctx.db, ctx.settings, user)
    ctx.commit()
    resp = ctx.redirect("/")
    ctx.set_session_cookie(resp, token)
    return resp


@router.get("/recover", response_class=HTMLResponse)
def recover_form(ctx: Ctx = Depends(ctx_dep)) -> Response:
    return ctx.render("recover.html", sent=False)


@router.post("/recover", response_class=HTMLResponse)
async def recover_submit(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    rl = ratelimit.hit(ctx.db, f"recover:{ctx.client_bucket}", 5, 3600)
    if rl.allowed:
        accounts.start_password_reset(ctx.db, str(form.get("email") or ""))
    ctx.commit()
    return ctx.render("recover.html", sent=True)  # uniform response: never reveals whether the account exists


@router.get("/reset/{token}", response_class=HTMLResponse)
def reset_form(token: str, ctx: Ctx = Depends(ctx_dep)) -> Response:
    return ctx.render("reset.html", token=token, errors={})


@router.post("/reset/{token}", response_class=HTMLResponse)
async def reset_submit(token: str, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    try:
        accounts.reset_password(ctx.db, token, str(form.get("password") or ""))
    except accounts.AccountError as exc:
        ctx.commit()
        return ctx.render("reset.html", 422, token=token, errors=exc.errors)
    ctx.commit()
    ctx.flash.append(("ok", "Password changed. Sign in with your new password."))
    return ctx.render("login.html", errors={}, email="")


# ---------------- MFA ----------------
def _mfa_user(ctx: Ctx) -> Any:
    if not ctx.user or not ctx.session:
        raise HTTPException(status_code=401)
    if not accounts.needs_mfa(ctx.settings, ctx.user):
        raise HTTPException(status_code=404)
    return ctx.user


@router.get("/mfa", response_class=HTMLResponse)
def mfa_form(ctx: Ctx = Depends(ctx_dep)) -> Response:
    user = _mfa_user(ctx)
    if ctx.mfa_ok:
        return ctx.redirect(HOME.get(user.role, "/"))
    if not user.totp_enabled:
        return ctx.redirect("/mfa/setup")
    return ctx.render("mfa.html", errors={})


@router.post("/mfa", response_class=HTMLResponse)
async def mfa_submit(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = _mfa_user(ctx)
    assert ctx.session is not None
    try:
        accounts.verify_mfa(ctx.db, ctx.settings, user, ctx.session, str(form.get("code") or ""))
    except accounts.LockedOut as exc:
        accounts.end_session(ctx.db, ctx.request.cookies.get(SESSION_COOKIE))
        audit.record(ctx.db, user.id, "mfa.lockout", "user", user.id)
        ctx.commit()
        resp = ctx.render("login.html", 429, errors={"form": str(exc)}, email="")
        resp.delete_cookie(SESSION_COOKIE, path="/")
        return resp
    except accounts.LoginFailed as exc:
        ctx.commit()
        return ctx.render("mfa.html", 401, errors={"code": str(exc)})
    ctx.commit()
    return ctx.redirect(HOME.get(user.role, "/"))


@router.get("/mfa/setup", response_class=HTMLResponse)
def mfa_setup(ctx: Ctx = Depends(ctx_dep)) -> Response:
    user = _mfa_user(ctx)
    if user.totp_enabled:
        return ctx.redirect("/mfa")
    secret = accounts.current_secret(ctx.settings, user) or accounts.begin_mfa_setup(ctx.settings, user)
    ctx.commit()
    uri = totp_uri(secret, user.email)
    buf = io.BytesIO()
    segno.make(uri).save(buf, kind="svg", xmldecl=False, scale=4, border=1, svgclass="qr-svg", omitsize=False)
    return ctx.render("mfa_setup.html", secret=secret, uri=uri, qr=buf.getvalue().decode(), errors={}, codes=None)


@router.post("/mfa/setup", response_class=HTMLResponse)
async def mfa_setup_confirm(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = _mfa_user(ctx)
    assert ctx.session is not None
    secret = accounts.current_secret(ctx.settings, user)
    try:
        codes = accounts.confirm_mfa_setup(ctx.db, ctx.settings, user, ctx.session, str(form.get("code") or ""))
    except accounts.AccountError as exc:
        ctx.commit()
        return ctx.render("mfa_setup.html", 422, secret=secret, uri="", qr="", errors=exc.errors, codes=None)
    ctx.commit()
    return ctx.render("mfa_setup.html", secret=None, uri="", qr="", errors={}, codes=codes, dest=HOME.get(user.role, "/"))


# ---------------- my reports ----------------
STAGES = ("Received", "Duplicate check", "Moderator review", "Outcome")


def _stage(status: str) -> int:
    return {"received": 2, "in_review": 3, "awaiting_evidence": 3}.get(status, 4)


@router.get("/mine", response_class=HTMLResponse)
def mine(ctx: Ctx = Depends(ctx_dep)) -> Response:
    user = ctx.need("report.own")
    reps = list(ctx.db.scalars(select(Report).where(Report.reporter_id == user.id).order_by(Report.id.desc())))
    rows = [{"r": r, "stage": _stage(r.status), "masked": mask_value(r.itype, r.indicator.norm_value) if r.itype != "message" else "Message"} for r in reps]
    return ctx.render("mine.html", rows=rows, stages=STAGES)


@router.post("/mine/{rid}/withdraw")
async def withdraw(rid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    await ctx.form()
    user = ctx.need("report.own")
    r = ctx.db.get(Report, rid)
    if r is None or r.reporter_id != user.id:
        raise HTTPException(status_code=404)
    if r.status in ("received", "in_review", "awaiting_evidence"):
        r.status = "withdrawn"
        audit.record(ctx.db, user.id, "report.withdrawn", "report", r.id)
        recompute_indicator(ctx.db, r.indicator, ctx.settings)
    ctx.commit()
    return ctx.redirect("/mine")


@router.post("/mine/{rid}/evidence")
async def add_evidence(rid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = ctx.need("report.own")
    r = ctx.db.get(Report, rid)
    if r is None or r.reporter_id != user.id:
        raise HTTPException(status_code=404)
    f = form.get("evidence")
    if r.status != "awaiting_evidence" or not isinstance(f, UploadFile):
        return ctx.redirect("/mine")
    try:
        sf = store_image(ctx.settings.storage_dir, await f.read(ctx.settings.max_upload_bytes + 1), ctx.settings.max_upload_bytes, ctx.settings.max_image_pixels)
    except UploadRejected as exc:
        ctx.flash.append(("err", str(exc)))
        return ctx.render("error.html", 422, title="Upload rejected", message=str(exc))
    ctx.db.add(Evidence(report_id=r.id, indicator_id=r.indicator_id, storage_name=sf.storage_name, mime=sf.mime, size=sf.size, sha256=sf.sha256, origin=r.origin))
    r.status = "in_review"
    audit.record(ctx.db, user.id, "report.evidence_added", "report", r.id)
    recompute_indicator(ctx.db, r.indicator, ctx.settings)
    ctx.commit()
    return ctx.redirect("/mine")


# ---------------- notifications ----------------
@router.get("/notifications", response_class=HTMLResponse)
def notifications(ctx: Ctx = Depends(ctx_dep)) -> Response:
    user = ctx.need("notifications.own")
    subs = {s.category: s for s in ctx.db.scalars(select(AlertSubscription).where(AlertSubscription.user_id == user.id, AlertSubscription.org_id.is_(None)))}
    pref = ctx.db.get(NotificationPref, user.id) or NotificationPref(user_id=user.id)
    recent = list(ctx.db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(15)))
    return ctx.render("notifications.html", subs=subs, pref=pref, recent=recent, cats=ALERT_CATEGORIES, saved=False)


@router.post("/notifications", response_class=HTMLResponse)
async def notifications_save(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = ctx.need("notifications.own")
    freq = str(form.get("frequency") or "instant")
    if freq not in ("instant", "daily", "weekly"):
        freq = "instant"
    existing = {s.category: s for s in ctx.db.scalars(select(AlertSubscription).where(AlertSubscription.user_id == user.id, AlertSubscription.org_id.is_(None)))}
    for c in ALERT_CATEGORIES:
        on = bool(form.get(f"cat_{c}"))
        s = existing.get(c)
        if s is None and on:
            ctx.db.add(AlertSubscription(user_id=user.id, category=c, frequency=freq, enabled=True))
        elif s is not None:
            s.enabled, s.frequency = on, freq
    pref = ctx.db.get(NotificationPref, user.id)
    if pref is None:
        pref = NotificationPref(user_id=user.id)
        ctx.db.add(pref)
    pref.on_new_verified = bool(form.get("on_new_verified"))
    pref.on_status_change = bool(form.get("on_status_change"))
    pref.on_org_updates = bool(form.get("on_org_updates"))
    pref.frequency = freq
    ctx.commit()
    ctx.flash.append(("ok", "Preferences saved."))
    return notifications(ctx)  # type: ignore[no-any-return]


# ---------------- settings ----------------
@router.get("/settings", response_class=HTMLResponse)
def settings_page(ctx: Ctx = Depends(ctx_dep)) -> Response:
    user = ctx.need_login()
    return ctx.render("settings.html", mfa_required=user.role in ctx.settings.mfa_roles)


@router.post("/settings", response_class=HTMLResponse)
async def settings_save(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = ctx.need_login()
    user.display_name = str(form.get("display_name") or "")[:120]
    lang = str(form.get("language") or "en")
    user.language = lang if lang in ("en", "sw") else "en"
    ctx.commit()
    ctx.flash.append(("ok", "Settings saved."))
    return ctx.render("settings.html", mfa_required=user.role in ctx.settings.mfa_roles)


@router.get("/settings/export")
def export_my_data(ctx: Ctx = Depends(ctx_dep)) -> Response:
    user = ctx.need_login()
    reps = ctx.db.scalars(select(Report).where(Report.reporter_id == user.id).order_by(Report.id))
    data = {
        "account": {"email": user.email, "name": user.display_name, "role": user.role, "created": user.created_at.isoformat()},
        "reports": [{"reference": r.ref, "type": r.itype, "value": r.raw_value, "category": r.category, "description": r.description, "status": r.status, "created": r.created_at.isoformat()} for r in reps],
    }
    return Response(json.dumps(data, indent=2), media_type="application/json", headers={"Content-Disposition": "attachment; filename=my-data.json", "Cache-Control": "no-store"})


@router.post("/settings/delete", response_class=HTMLResponse)
async def delete_me(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = ctx.need_login()
    reason = str(form.get("reason") or "").strip()
    if user.role not in ("reporter", "contributor"):
        return ctx.render("error.html", 403, title="Ask an administrator", message="Staff accounts are removed by a platform administrator.")
    if len(reason) < 8 or not form.get("confirm"):
        return ctx.render("error.html", 422, title="Confirm deletion", message="Give a reason (8+ characters) and tick the confirmation box.")
    accounts.delete_account(ctx.db, user, reason)
    ctx.commit()
    resp = ctx.redirect("/")
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp
