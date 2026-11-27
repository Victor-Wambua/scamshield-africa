"""Public pages: check, search, record, report, analyse, correction, evidence download."""

from __future__ import annotations

import hmac
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from sqlalchemy import select, text
from starlette.datastructures import UploadFile

from .. import ratelimit
from ..analysis import analyse_message
from ..corrections import CorrectionInvalid, submit_correction
from ..models import CATEGORIES, Evidence, Indicator, Report
from ..orgs import COUNTIES
from ..permissions import can
from ..reports import (
    GENERAL_ADVICE,
    SAFETY_ADVICE,
    ReportInvalid,
    SubmitInput,
    analysis_context,
    browse,
    exact_lookup,
    history,
    public_view,
    submit_report,
)
from ..security import csrf_for
from ..tenancy import TenantScope, TenantViolation
from ..uploads import path_for
from .deps import Ctx
from .guards import ctx_dep

router = APIRouter()


@router.get("/healthz")
def healthz(ctx: Ctx = Depends(ctx_dep)) -> Response:
    ok = True
    try:
        ctx.db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        ok = False
    return Response(content='{"status":"%s"}' % ("ok" if ok else "degraded"), media_type="application/json", status_code=200 if ok else 503)


@router.get("/", response_class=HTMLResponse)
def home(ctx: Ctx = Depends(ctx_dep)) -> Response:
    inds = browse(ctx.db, status="verified", limit=3)
    verified = [public_view(i, exact=False) for i in inds]
    return ctx.render("home.html", verified=verified, advice=GENERAL_ADVICE)


def _reveal(ctx: Ctx, ind_id: int) -> str:
    return csrf_for(ctx.settings.secret_key, f"reveal:{ind_id}")[:24]


@router.get("/search", response_class=HTMLResponse)
def search(request: Request, ctx: Ctx = Depends(ctx_dep), q: str = "", type: str = "", status: str = "", category: str = "") -> Response:
    q = q.strip()[:600]
    results: list[dict[str, Any]] = []
    error = None
    if q:
        r = ratelimit.hit(ctx.db, f"lookup:{ctx.client_bucket}", 60, 60)
        ctx.commit()
        if not r.allowed:
            return ctx.render("error.html", 429, title="Too many searches", message=f"Please wait {r.retry_after} seconds and try again.")
        inds = exact_lookup(ctx.db, q, type or None)
        staff_view = can(ctx.role, "moderation.queue")
        for i in inds:
            d = public_view(i, exact=True, staff=staff_view)
            d["reveal"] = _reveal(ctx, i.id)
            results.append(d)
        if not inds and not any([type]) and not _looks_valid(q):
            error = "That does not look like a phone number, link, email or wallet. Check it and try again."
    else:
        inds = browse(ctx.db, itype=type or None, status=status or None, category=category or None)
        results = [public_view(i, exact=False) for i in inds]
    if q and status:
        results = [r_ for r_ in results if r_["status"] == status]
    if q and category:
        results = [r_ for r_ in results if r_["risk_category"] == category]
    return ctx.render("search.html", q=q, type=type, status=status, category=category, results=results, error=error, categories=CATEGORIES)


def _looks_valid(q: str) -> bool:
    from ..reports import candidate_types

    return bool(candidate_types(q, None))


@router.get("/i/{ind_id}", response_class=HTMLResponse)
def indicator(ind_id: int, ctx: Ctx = Depends(ctx_dep), v: str = "") -> Response:
    ind = ctx.db.get(Indicator, ind_id)
    staff = can(ctx.role, "moderation.queue") and (not ctx.user or ctx.mfa_ok or ctx.role not in ctx.settings.mfa_roles)
    if ind is None or (ind.status not in ("unverified", "verified") and not staff):
        raise HTTPException(status_code=404)
    revealed = bool(v) and hmac.compare_digest(v, _reveal(ctx, ind.id))
    view = public_view(ind, exact=revealed, staff=staff)
    return ctx.render("indicator.html", i=view, staff=staff, history=history(ctx.db, ind, staff), advice=SAFETY_ADVICE.get(ind.risk_category, SAFETY_ADVICE["other"]), general=GENERAL_ADVICE)


# ---------------- report ----------------
def _report_values(form: Any) -> dict[str, str]:
    keys = ("itype", "value", "message_text", "category", "description", "incident_date", "amount_kes", "county", "contact_email")
    d = {k: str(form.get(k) or "") for k in keys}
    d["category"] = d["category"] or "other"
    for k in ("consent_privacy", "consent_truth", "consent_share_partners", "consent_contact"):
        d[k] = "1" if form.get(k) else ""
    return d


@router.get("/report", response_class=HTMLResponse)
def report_form(ctx: Ctx = Depends(ctx_dep), type: str = "") -> Response:
    return ctx.render("report.html", errors={}, v={"itype": type, "category": "other"}, categories=CATEGORIES, counties=COUNTIES)


@router.post("/report", response_class=HTMLResponse)
async def report_submit(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    values = _report_values(form)
    limit_key = f"report:{ctx.user.id if ctx.user else ctx.client_bucket}"
    rl = ratelimit.hit(ctx.db, limit_key, ctx.settings.report_rate_per_hour, 3600)
    if not rl.allowed:
        ctx.commit()
        return ctx.render("error.html", 429, title="Too many reports", message=f"You have sent many reports recently. Please try again in about {max(1, rl.retry_after // 60)} minutes.")
    errors: dict[str, str] = {}
    date_v = None
    if values["incident_date"]:
        try:
            date_v = datetime.fromisoformat(values["incident_date"])
        except ValueError:
            errors["incident_date"] = "Enter a valid date."
    amount = None
    if values["amount_kes"]:
        try:
            amount = int(values["amount_kes"])
        except ValueError:
            errors["amount_kes"] = "Enter a whole number of shillings."
    files = []
    for f in form.getlist("evidence"):
        if isinstance(f, UploadFile) and f.filename:
            files.append(await f.read(ctx.settings.max_upload_bytes + 1))
    inp = SubmitInput(
        itype=values["itype"], value=values["value"], description=values["description"], category=values["category"],
        message_text=values["message_text"] or None, incident_date=date_v, amount_kes=amount, county=values["county"] or None,
        consent_privacy=bool(values["consent_privacy"]), consent_truth=bool(values["consent_truth"]),
        consent_share_partners=bool(values["consent_share_partners"]), consent_contact=bool(values["consent_contact"]),
        contact_email=values["contact_email"] or None, files=files,
    )
    if errors:
        ctx.commit()
        return ctx.render("report.html", 422, errors=errors, v=values, categories=CATEGORIES, counties=COUNTIES)
    try:
        res = submit_report(ctx.db, ctx.settings, inp, reporter=ctx.user, bucket=ctx.client_bucket, owning_org_id=ctx.user.org_id if ctx.user and ctx.user.org_id and ctx.user.role in ("org_analyst", "org_admin") else None)
    except ReportInvalid as exc:
        ctx.db.rollback()
        return ctx.render("report.html", 422, errors=exc.errors, v=values, categories=CATEGORIES, counties=COUNTIES)
    ctx.commit()
    return ctx.redirect(f"/report/done?ref={res.report.ref}&dup={int(res.is_duplicate)}&ind={int(res.independent)}")


@router.get("/report/done", response_class=HTMLResponse)
def report_done(ctx: Ctx = Depends(ctx_dep), ref: str = "", dup: int = 0, ind: int = 1) -> Response:
    safe_ref = ref if ref.startswith("R-") and ref[2:].isdigit() else ""
    return ctx.render("report_done.html", ref=safe_ref, dup=bool(dup), ind=bool(ind))


# ---------------- analyse ----------------
def _segments(text_: str, highlights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pos = 0
    for h in highlights:
        if h["start"] < pos:
            continue
        if h["start"] > pos:
            out.append({"text": text_[pos : h["start"]], "signal": None})
        out.append({"text": text_[h["start"] : h["end"]], "signal": h["signal"]})
        pos = h["end"]
    if pos < len(text_):
        out.append({"text": text_[pos:], "signal": None})
    return out


@router.get("/analyse", response_class=HTMLResponse)
def analyse_form(ctx: Ctx = Depends(ctx_dep)) -> Response:
    return ctx.render("analyse.html", text="", result=None, error=None, segments=[])


@router.post("/analyse", response_class=HTMLResponse)
async def analyse_submit(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    body = str(form.get("text") or "")
    rl = ratelimit.hit(ctx.db, f"analyse:{ctx.client_bucket}", 30, 3600)
    ctx.commit()
    if not rl.allowed:
        return ctx.render("error.html", 429, title="Too many analyses", message="Please try again later.")
    if not 10 <= len(body.strip()) <= 5000:
        return ctx.render("analyse.html", 422, text=body, result=None, segments=[], error="Enter between 10 and 5,000 characters.")
    res = analyse_message(body, analysis_context(ctx.db))
    d = res.as_dict()
    return ctx.render("analyse.html", text=body, result=d, error=None, segments=_segments(body, d["highlights"]))


# ---------------- correction ----------------
@router.get("/correct/{ind_id}", response_class=HTMLResponse)
def correct_form(ind_id: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    ind = ctx.db.get(Indicator, ind_id)
    if ind is None or ind.status not in ("unverified", "verified"):
        raise HTTPException(status_code=404)
    return ctx.render("correct.html", ind_id=ind_id, errors={}, v={})


@router.post("/correct/{ind_id}", response_class=HTMLResponse)
async def correct_submit(ind_id: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    rl = ratelimit.hit(ctx.db, f"correct:{ctx.client_bucket}", ctx.settings.correction_rate_per_hour, 3600)
    if not rl.allowed:
        ctx.commit()
        return ctx.render("error.html", 429, title="Too many requests", message="Please try again later.")
    v = {k: str(form.get(k) or "") for k in ("relationship", "explanation", "contact_email", "acknowledged", "urgent_legal")}
    try:
        c = submit_correction(ctx.db, ctx.settings, ind_id, v["relationship"], v["explanation"], v["contact_email"], bool(v["acknowledged"]), bool(v["urgent_legal"]))
    except CorrectionInvalid as exc:
        ctx.db.rollback()
        if "indicator" in exc.errors:
            raise HTTPException(status_code=404) from exc
        return ctx.render("correct.html", 422, ind_id=ind_id, errors=exc.errors, v=v)
    ctx.commit()
    return ctx.render("correct_done.html", ref=c.ref, due=c.due_at.date().isoformat())


# ---------------- misc ----------------
@router.get("/about", response_class=HTMLResponse)
def about(ctx: Ctx = Depends(ctx_dep)) -> Response:
    return ctx.render("about.html")


@router.get("/lang/{code}")
def set_lang(code: str, request: Request, ctx: Ctx = Depends(ctx_dep)) -> Response:
    if code not in ("en", "sw"):
        raise HTTPException(status_code=404)
    ref = urlparse(request.headers.get("referer", "")).path or "/"
    if not ref.startswith("/") or ref.startswith("//"):
        ref = "/"
    resp = RedirectResponse(ref, status_code=303)
    resp.set_cookie("ss_lang", code, max_age=86400 * 365, samesite="lax", secure=ctx.settings.cookie_secure)
    if ctx.user:
        ctx.user.language = code
        ctx.commit()
    ctx.attach_cookies(resp)
    return resp


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> str:
    return "User-agent: *\nDisallow: /mod\nDisallow: /org\nDisallow: /admin\nDisallow: /dev\nDisallow: /evidence\n"


@router.get("/evidence/{ev_id}")
def evidence_file(ev_id: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    """Authorised evidence download: submitter, moderators/admins, or the owning org's analysts only."""
    user = ctx.need_login()
    ev = ctx.db.get(Evidence, ev_id)
    if ev is None:
        raise HTTPException(status_code=404)
    rep = ctx.db.get(Report, ev.report_id)
    allowed = False
    if rep is not None:
        if rep.reporter_id == user.id:
            allowed = True
        elif can(user.role, "evidence.view_all"):
            allowed = True
        elif can(user.role, "org.evidence"):
            try:
                TenantScope(ctx.db, user.org_id).evidence_item(ev_id)
                allowed = True
            except TenantViolation:
                allowed = False
    if not allowed:
        raise HTTPException(status_code=404)  # do not reveal existence
    p = path_for(ctx.settings.storage_dir, ev.storage_name)
    if p is None:
        raise HTTPException(status_code=404)
    return FileResponse(p, media_type=ev.mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Content-Disposition": "inline"})


_ = select  # keep import for type checkers
