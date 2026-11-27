"""Moderation, corrections, audit log and platform administration."""

from __future__ import annotations

import csv
import io
from statistics import median
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, or_, select

from .. import accounts, audit
from ..corrections import CorrectionError, decide_correction, queue as correction_queue
from ..models import AuditLog, Correction, Evidence, Indicator, Organisation, Report, ReviewEvent, User, ROLES
from ..moderation import ModerationError, decide
from ..permissions import PERMISSIONS
from ..reports import COUNTED, history, message_priors, policy_of
from ..rules import ReportFact, evaluate_verification, independent_count
from .deps import Ctx
from .guards import ctx_dep

router = APIRouter()


@router.get("/mod", response_class=HTMLResponse)
def queue(ctx: Ctx = Depends(ctx_dep), f: str = "needs", q: str = "") -> Response:
    ctx.need("moderation.queue")
    db = ctx.db
    stmt = select(Report)
    if f == "needs":
        stmt = stmt.where(Report.status.in_(("received", "in_review")))
    elif f == "decided":
        stmt = stmt.where(Report.status.in_(("accepted", "rejected", "merged", "awaiting_evidence")))
    if q.strip():
        like = f"%{q.strip()[:40]}%"
        stmt = stmt.where(or_(Report.ref.ilike(like), Report.raw_value.ilike(like)))
    reps = list(db.scalars(stmt.order_by(Report.id.desc()).limit(100)))
    ev_counts = dict(db.execute(select(Evidence.report_id, func.count()).group_by(Evidence.report_id)).all())
    waiting = db.scalar(select(func.count()).select_from(Report).where(Report.status.in_(("received", "in_review")))) or 0
    awaiting = db.scalar(select(func.count()).select_from(Report).where(Report.status == "awaiting_evidence")) or 0
    corr = db.scalar(select(func.count()).select_from(Correction).where(Correction.status == "open")) or 0
    firsts: dict[int, Any] = {}
    for rid, ts in db.execute(select(ReviewEvent.report_id, func.min(ReviewEvent.created_at)).where(ReviewEvent.report_id.is_not(None)).group_by(ReviewEvent.report_id)):
        firsts[rid] = ts
    hrs = [(firsts[r.id] - r.created_at).total_seconds() / 3600 for r in db.scalars(select(Report)) if r.id in firsts]
    med = f"{median(hrs):.1f} h" if hrs else "None yet"
    rows = [{"r": r, "ev": ev_counts.get(r.id, 0), "same": not r.counts_independent, "dup": r.duplicate_of_id is not None} for r in reps]
    return ctx.render("mod_queue.html", rows=rows, f=f, q=q, kpi={"waiting": waiting, "awaiting": awaiting, "corr": corr, "median": med})


@router.get("/mod/corrections", response_class=HTMLResponse)
def corrections(ctx: Ctx = Depends(ctx_dep)) -> Response:
    ctx.need("corrections.handle")
    return ctx.render("mod_corrections.html", items=correction_queue(ctx.db))


@router.post("/mod/corrections/{cid}/decide", response_class=HTMLResponse)
async def correction_decide(cid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = ctx.need("corrections.handle")
    try:
        decide_correction(ctx.db, ctx.settings, user, cid, str(form.get("decision") or ""), str(form.get("reason") or ""))
        ctx.commit()
        ctx.flash.append(("ok", "Decision recorded."))
    except CorrectionError as exc:
        ctx.db.rollback()
        ctx.flash.append(("err", str(exc)))
    return ctx.render("mod_corrections.html", items=correction_queue(ctx.db))


@router.get("/mod/{rid}", response_class=HTMLResponse)
def review(rid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    ctx.need("moderation.queue")
    return _review_page(ctx, rid)


def _review_page(ctx: Ctx, rid: int, status: int = 200) -> Response:
    db = ctx.db
    rep = db.get(Report, rid)
    if rep is None:
        raise HTTPException(status_code=404)
    ind = db.get(Indicator, rep.indicator_id)
    assert ind is not None
    others = list(db.scalars(select(Report).where(Report.indicator_id == ind.id, Report.id != rep.id).order_by(Report.id)))
    counted = [r for r in db.scalars(select(Report).where(Report.indicator_id == ind.id)) if r.status in COUNTED or r.id == rep.id]
    n = independent_count([ReportFact(r.id, r.reporter_id, r.device_bucket) for r in counted])
    has_primary = db.scalar(select(Evidence.id).where(Evidence.indicator_id == ind.id, Evidence.primary_by_moderator.is_(True)).limit(1)) is not None
    decision = evaluate_verification(n, has_primary, policy_of(ctx.settings))
    evidence = list(db.scalars(select(Evidence).where(Evidence.report_id == rep.id)))
    similar = []
    text = rep.message_text or (rep.description if rep.itype == "message" else None)
    if text:
        similar = [p for p in message_priors(db, text, exclude_report_id=rep.id)]
    targets = list(db.scalars(select(Indicator).where(Indicator.id != ind.id, Indicator.type == ind.type, Indicator.status != "removed").order_by(Indicator.id.desc()).limit(30)))
    return ctx.render("mod_review.html", status, r=rep, ind=ind, others=others, evidence=evidence, similar=similar, targets=targets, hist=history(db, ind, True),
                      verify=decision, independent=n, reporter_label=f"Reporter #{rep.reporter_id}" if rep.reporter_id else "Anonymous reporter")


@router.post("/mod/{rid}/decide", response_class=HTMLResponse)
async def review_decide(rid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    user = ctx.need("moderation.decide")
    data = None
    f = form.get("file")
    if hasattr(f, "read") and getattr(f, "filename", ""):
        data = await f.read(ctx.settings.max_upload_bytes + 1)
    target = form.get("target_indicator_id")
    try:
        decide(ctx.db, ctx.settings, user, rid, str(form.get("action") or ""), str(form.get("reason") or ""),
               target_indicator_id=int(str(target)) if target and str(target).isdigit() else None, file_bytes=data)
        ctx.commit()
        ctx.flash.append(("ok", "Action recorded and audited."))
        return _review_page(ctx, rid)
    except ModerationError as exc:
        ctx.db.rollback()
        ctx.flash.append(("err", str(exc)))
        return _review_page(ctx, rid, 422)


@router.get("/audit", response_class=HTMLResponse)
def audit_page(ctx: Ctx = Depends(ctx_dep), action: str = "", verify: int = 0) -> Response:
    ctx.need("audit.read")
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(200)
    if action:
        stmt = select(AuditLog).where(AuditLog.action.like(action[:40] + "%")).order_by(AuditLog.id.desc()).limit(200)
    chain = audit.verify_chain(ctx.db) if verify else None
    return ctx.render("audit.html", rows=list(ctx.db.scalars(stmt)), action=action, chain=chain)


@router.get("/audit.csv")
def audit_csv(ctx: Ctx = Depends(ctx_dep)) -> Response:
    ctx.need("audit.read")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "time", "actor", "action", "target_type", "target_id", "reason", "hash"])
    for r in ctx.db.scalars(select(AuditLog).order_by(AuditLog.id)):
        w.writerow([r.id, r.ts.isoformat(), r.actor_id or "", _cell(r.action), r.target_type, r.target_id, _cell(r.reason), r.hash])
    return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit.csv", "Cache-Control": "no-store"})


def _cell(v: str) -> str:
    return "'" + v if v[:1] in ("=", "+", "-", "@") else v


# ---------------- platform admin ----------------
@router.get("/admin", response_class=HTMLResponse)
def admin_users(ctx: Ctx = Depends(ctx_dep), q: str = "") -> Response:
    ctx.need("admin.users")
    stmt = select(User).where(User.deleted.is_(False)).order_by(User.id)
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q[:60]}%"))
    return ctx.render("admin_users.html", users=list(ctx.db.scalars(stmt.limit(200))), roles=ROLES, q=q, orgs=list(ctx.db.scalars(select(Organisation))))


@router.post("/admin/users/{uid}/role", response_class=HTMLResponse)
async def admin_role(uid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    admin = ctx.need("admin.users")
    u = ctx.db.get(User, uid)
    role, reason = str(form.get("role") or ""), str(form.get("reason") or "").strip()
    org_raw = str(form.get("org_id") or "")
    if u is None:
        raise HTTPException(status_code=404)
    if role not in ROLES or len(reason) < 8:
        ctx.flash.append(("err", "Choose a valid role and give a reason of at least 8 characters."))
    elif u.id == admin.id:
        ctx.flash.append(("err", "You cannot change your own role."))
    elif role in ("org_analyst", "org_admin") and not (org_raw.isdigit() and ctx.db.get(Organisation, int(org_raw))):
        ctx.flash.append(("err", "Organisation roles need an organisation."))
    else:
        old = u.role
        u.role = role
        u.org_id = int(org_raw) if role in ("org_analyst", "org_admin") else None
        for s in list(ctx.db.scalars(select(accounts.Session).where(accounts.Session.user_id == u.id))):
            ctx.db.delete(s)  # force re-authentication with new privileges
        audit.record(ctx.db, admin.id, "user.role_changed", "user", u.id, reason, {"from": old, "to": role})
        ctx.commit()
        ctx.flash.append(("ok", "Role changed. The user must sign in again."))
    return admin_users(ctx)  # type: ignore[no-any-return]


@router.post("/admin/users/{uid}/restrict", response_class=HTMLResponse)
async def admin_restrict(uid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    admin = ctx.need("admin.users")
    u = ctx.db.get(User, uid)
    reason = str(form.get("reason") or "").strip()
    if u is None:
        raise HTTPException(status_code=404)
    if len(reason) < 8:
        ctx.flash.append(("err", "A reason of at least 8 characters is required."))
    elif u.id == admin.id:
        ctx.flash.append(("err", "You cannot restrict yourself."))
    else:
        u.restricted = not u.restricted
        u.restricted_reason = reason if u.restricted else None
        audit.record(ctx.db, admin.id, "user.restricted" if u.restricted else "user.restored", "user", u.id, reason)
        ctx.commit()
        ctx.flash.append(("ok", "Account restricted." if u.restricted else "Account restored."))
    return admin_users(ctx)  # type: ignore[no-any-return]


@router.get("/admin/roles", response_class=HTMLResponse)
def admin_roles(ctx: Ctx = Depends(ctx_dep)) -> Response:
    ctx.need("admin.users")
    perms = sorted({p for s in PERMISSIONS.values() for p in s})
    return ctx.render("admin_roles.html", matrix=PERMISSIONS, perms=perms, roles=ROLES)


@router.get("/admin/orgs", response_class=HTMLResponse)
def admin_orgs(ctx: Ctx = Depends(ctx_dep)) -> Response:
    ctx.need("admin.orgs")
    return ctx.render("admin_orgs.html", orgs=list(ctx.db.scalars(select(Organisation).order_by(Organisation.id))))


@router.post("/admin/orgs", response_class=HTMLResponse)
async def admin_org_create(ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    admin = ctx.need("admin.orgs")
    name, kind = str(form.get("name") or "").strip(), str(form.get("kind") or "bank")
    if not 3 <= len(name) <= 200 or ctx.db.scalar(select(Organisation.id).where(Organisation.name == name)):
        ctx.flash.append(("err", "Enter a unique organisation name (3 to 200 characters)."))
    else:
        org = Organisation(name=name, kind=kind[:40], status="approved")
        ctx.db.add(org)
        ctx.db.flush()
        audit.record(ctx.db, admin.id, "org.approved", "organisation", org.id, f"approved partner {name}")
        ctx.commit()
        ctx.flash.append(("ok", "Organisation approved."))
    return admin_orgs(ctx)  # type: ignore[no-any-return]


@router.post("/admin/orgs/{oid}/invite", response_class=HTMLResponse)
async def admin_org_invite(oid: int, ctx: Ctx = Depends(ctx_dep)) -> Response:
    form = await ctx.form()
    admin = ctx.need("admin.orgs")
    org = ctx.db.get(Organisation, oid)
    role = str(form.get("role") or "org_analyst")
    if org is None or role not in ("org_analyst", "org_admin"):
        raise HTTPException(status_code=404)
    from ..security import new_token

    try:
        u = accounts.register(ctx.db, str(form.get("email") or ""), new_token() + "a1", "", True, role=role, org_id=org.id)
    except accounts.AccountError as exc:
        ctx.db.rollback()
        ctx.flash.append(("err", "; ".join(exc.errors.values())))
        return admin_orgs(ctx)  # type: ignore[no-any-return]
    token = accounts.start_password_reset(ctx.db, u.email)
    audit.record(ctx.db, admin.id, "org.user_invited", "user", u.id, detail={"org": org.id, "role": role})
    ctx.commit()
    ctx.flash.append(("ok", f"Invited. Pilot (sandbox mail): give them this one-time link: /reset/{token}"))
    return admin_orgs(ctx)  # type: ignore[no-any-return]
