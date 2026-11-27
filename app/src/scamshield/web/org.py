"""Institutional dashboard and developer portal. All org data goes through TenantScope."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select

from .. import audit, orgs
from ..models import CATEGORIES, AlertSubscription, ApiKey, Case, Evidence, Indicator, Report
from ..tenancy import TenantScope, TenantViolation
from .deps import Ctx
from .guards import ctx_dep

router = APIRouter()


def scope_for(ctx: Ctx, permission: str) -> TenantScope:
    user = ctx.need(permission)
    try:
        return TenantScope(ctx.db, user.org_id)
    except TenantViolation as exc:
        raise HTTPException(status_code=403) from exc


@router.get("/org", response_class=HTMLResponse)
def dashboard(ctx: Ctx = Depends(ctx_dep), days: int = 30) -> Response:
    scope = scope_for(ctx, "org.analytics")
    days = days if days in (7, 30, 90) else 30
    data = orgs.analytics(scope, days)
    pts = data["series"]
    mx = max([n for _, n in pts] + [1])
    w, h = 600, 160
    line = " ".join(f"{i * w / max(len(pts) - 1, 1):.1f},{h - (n / mx) * (h - 20) - 5:.1f}" for i, (_, n) in enumerate(pts))
    return ctx.render("org_dash.html", d=data, line=line, mx=mx, w=w, h=h, org=ctx.user.org if ctx.user else None, trends=orgs.network_trends(ctx.db, days))


@router.get("/org/campaigns", response_class=HTMLResponse)
def campaigns(ctx: Ctx = Depends(ctx_dep), category: str = "") -> Response:
    scope_for(ctx, "org.analytics")
    items = orgs.threat_intel(ctx.db, category or None)
    return ctx.render("org_campaigns.html", items=items, category=category, categories=CATEGORIES, cases=list(ctx.db.scalars(scope_for(ctx, "org.cases").cases())))


@router.get("/org/reports", response_class=HTMLResponse)
def own_reports(ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope = scope_for(ctx, "org.analytics")
    return ctx.render("org_reports.html", reps=list(ctx.db.scalars(scope.reports().order_by(Report.id.desc()).limit(200))))


@router.get("/org/reports/{rid}", response_class=HTMLResponse)
def own_report(rid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope = scope_for(ctx, "org.evidence")
    try:
        r = scope.report(rid)
    except TenantViolation as exc:
        raise HTTPException(status_code=404) from exc
    ev = list(ctx.db.scalars(select(Evidence).where(Evidence.report_id == r.id)))
    return ctx.render("org_report.html", r=r, evidence=ev)


@router.get("/org/cases", response_class=HTMLResponse)
def cases(ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope = scope_for(ctx, "org.cases")
    return ctx.render("org_cases.html", cases=list(ctx.db.scalars(scope.cases().order_by(Case.id.desc()))))


@router.post("/org/cases", response_class=HTMLResponse)
async def case_create(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "org.cases")
    title = str(form.get("title") or "").strip()
    if not 3 <= len(title) <= 200:
        ctx.flash.append(("err", "Give the case a title (3 to 200 characters)."))
        return cases(ctx)
    case = scope.create_case(title, ctx.user.id if ctx.user else 0)
    for raw in form.getlist("indicator_id"):
        if str(raw).isdigit():
            ind = ctx.db.get(Indicator, int(str(raw)))
            if ind is not None and ind.status in ("verified", "unverified"):
                scope.link_indicator(case, ind.id)
    audit.record(ctx.db, ctx.user.id if ctx.user else None, "case.created", "case", case.id, detail={"org": scope.org_id})
    ctx.commit()
    return ctx.redirect(f"/org/cases/{case.id}")


@router.get("/org/cases/{cid}", response_class=HTMLResponse)
def case_detail(cid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope = scope_for(ctx, "org.cases")
    try:
        case = scope.case(cid)
    except TenantViolation as exc:
        raise HTTPException(status_code=404) from exc
    ids = scope.case_indicator_ids(cid)
    inds = list(ctx.db.scalars(select(Indicator).where(Indicator.id.in_(ids or [0]))))
    return ctx.render("org_case.html", case=case, inds=inds, notes=scope.notes(cid))


@router.post("/org/cases/{cid}/note")
async def case_note(cid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "org.cases")
    body = str(form.get("body") or "").strip()
    try:
        if 1 <= len(body) <= 4000:
            scope.add_note(cid, ctx.user.id if ctx.user else 0, body)
            ctx.commit()
    except TenantViolation as exc:
        raise HTTPException(status_code=404) from exc
    return ctx.redirect(f"/org/cases/{cid}")


@router.post("/org/cases/{cid}/status")
async def case_status(cid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "org.cases")
    status = str(form.get("status") or "")
    try:
        if status in ("open", "closed"):
            scope.set_case_status(cid, status)
            ctx.commit()
    except TenantViolation as exc:
        raise HTTPException(status_code=404) from exc
    return ctx.redirect(f"/org/cases/{cid}")


@router.post("/org/cases/{cid}/link")
async def case_link(cid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "org.cases")
    raw = str(form.get("indicator_id") or "")
    try:
        case = scope.case(cid)
        ind = ctx.db.get(Indicator, int(raw)) if raw.isdigit() else None
        if ind is not None and ind.status in ("verified", "unverified"):
            scope.link_indicator(case, ind.id)
            ctx.commit()
    except TenantViolation as exc:
        raise HTTPException(status_code=404) from exc
    return ctx.redirect(f"/org/cases/{cid}")


@router.get("/org/exports", response_class=HTMLResponse)
def exports(ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope_for(ctx, "org.export")
    return ctx.render("org_exports.html")


@router.get("/org/export.csv")
def export_csv(ctx: Ctx = Depends(ctx_dep), days: int = 90) -> Response:
    scope = scope_for(ctx, "org.export")
    days = min(max(days, 1), 365)
    body = orgs.export_csv(scope, days)
    audit.record(ctx.db, ctx.user.id if ctx.user else None, "org.export", "organisation", scope.org_id, detail={"days": days})
    ctx.commit()
    return Response(body, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=scamshield-org-export.csv", "Cache-Control": "no-store"})


@router.get("/org/alerts", response_class=HTMLResponse)
def alerts(ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope = scope_for(ctx, "org.alerts")
    return ctx.render("org_alerts.html", subs=list(ctx.db.scalars(scope.alerts())), categories=CATEGORIES)


@router.post("/org/alerts", response_class=HTMLResponse)
async def alert_create(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "org.alerts")
    cat, freq = str(form.get("category") or ""), str(form.get("frequency") or "instant")
    if cat in CATEGORIES and freq in ("instant", "daily", "weekly") and ctx.user:
        ctx.db.add(AlertSubscription(user_id=ctx.user.id, org_id=scope.org_id, category=cat, frequency=freq))
        ctx.commit()
    return ctx.redirect("/org/alerts")


@router.post("/org/alerts/{aid}/toggle")
async def alert_toggle(aid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "org.alerts")
    try:
        a = scope.alert(aid)
    except TenantViolation as exc:
        raise HTTPException(status_code=404) from exc
    if str(form.get("delete") or ""):
        ctx.db.delete(a)
    else:
        a.enabled = not a.enabled
    ctx.commit()
    return ctx.redirect("/org/alerts")


# ---------------- developer portal ----------------
@router.get("/dev", response_class=HTMLResponse)
def dev_keys(ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope = scope_for(ctx, "dev.usage")
    return ctx.render("dev_keys.html", keys=list(ctx.db.scalars(scope.keys().order_by(ApiKey.id.desc()))), scopes=orgs.SCOPES, new_key=None, can_manage=bool(ctx.user and ctx.user.role == "org_admin"))


@router.post("/dev/keys", response_class=HTMLResponse)
async def dev_key_create(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "dev.keys")
    assert ctx.user is not None
    try:
        key, full = orgs.create_key(scope, ctx.user, str(form.get("name") or ""), [str(s) for s in form.getlist("scopes")], str(form.get("environment") or "test"), ctx.settings)
    except ValueError as exc:
        ctx.flash.append(("err", str(exc)))
        return dev_keys(ctx)
    ctx.commit()
    return ctx.render("dev_keys.html", keys=list(ctx.db.scalars(scope.keys())), scopes=orgs.SCOPES, new_key=full, can_manage=True)


@router.post("/dev/keys/{kid}/revoke", response_class=HTMLResponse)
async def dev_key_revoke(kid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    scope = scope_for(ctx, "dev.keys")
    reason = str(form.get("reason") or "").strip()
    if len(reason) < 4:
        ctx.flash.append(("err", "Give a short reason for revoking."))
        return dev_keys(ctx)
    try:
        scope.revoke_key(kid)
    except TenantViolation as exc:
        raise HTTPException(status_code=404) from exc
    audit.record(ctx.db, ctx.user.id if ctx.user else None, "apikey.revoked", "api_key", kid, reason)
    ctx.commit()
    return ctx.redirect("/dev")


@router.get("/dev/docs", response_class=HTMLResponse)
def dev_docs(ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope_for(ctx, "dev.usage")
    return ctx.render("dev_docs.html")


@router.get("/dev/usage", response_class=HTMLResponse)
def dev_usage(ctx: Ctx = Depends(ctx_dep)) -> Response:
    scope = scope_for(ctx, "dev.usage")
    return ctx.render("dev_usage.html", u=orgs.usage_summary(scope, 7), keys=list(ctx.db.scalars(scope.keys())))
