"""Moderator workflow: every action validates permission and reason, writes review history + audit."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .config import Settings
from .models import Evidence, Indicator, Report, ReviewEvent, User, utcnow
from .notify import dispatch_new_verified, notify_user
from .permissions import can
from .reports import COUNTED, LIVE, policy_of, recompute_indicator
from .rules import ReportFact, evaluate_verification, independent_count
from .uploads import UploadRejected, store_image

ACTIONS = ("accept", "verify", "mark_unverified", "request_evidence", "reject", "merge", "restrict_reporter", "attach_evidence")
MIN_REASON = 8


class ModerationError(Exception):
    pass


def _event(db: Session, ind_id: int, rep: Report | None, actor: User, action: str, reason: str) -> None:
    db.add(ReviewEvent(indicator_id=ind_id, report_id=rep.id if rep else None, actor_id=actor.id, action=action, reason=reason))


def _preview_independent(db: Session, ind: Indicator, extra: Report) -> int:
    reps = [r for r in db.scalars(select(Report).where(Report.indicator_id == ind.id)) if r.status in COUNTED or r.id == extra.id]
    return independent_count([ReportFact(r.id, r.reporter_id, r.device_bucket, True) for r in reps])


def decide(
    db: Session,
    settings: Settings,
    moderator: User,
    report_id: int,
    action: str,
    reason: str,
    *,
    target_indicator_id: int | None = None,
    file_bytes: bytes | None = None,
) -> Report:
    if not can(moderator.role, "moderation.decide"):
        raise ModerationError("You do not have permission to moderate.")
    if action not in ACTIONS:
        raise ModerationError("Unknown action.")
    reason = (reason or "").strip()
    if len(reason) < MIN_REASON:
        raise ModerationError(f"A reason of at least {MIN_REASON} characters is required.")
    rep = db.get(Report, report_id)
    if rep is None:
        raise ModerationError("Report not found.")
    if rep.reporter_id == moderator.id and action != "restrict_reporter":
        raise ModerationError("You cannot review your own report.")
    ind = db.get(Indicator, rep.indicator_id)
    assert ind is not None
    reporter = db.get(User, rep.reporter_id) if rep.reporter_id else None

    if action in ("accept", "mark_unverified"):
        if rep.status in ("rejected", "withdrawn"):
            raise ModerationError("This report was already closed.")
        rep.status = "accepted"
        if ind.status in ("pending", "verified", "removed") and (action == "mark_unverified" or ind.status == "pending"):
            if ind.status == "removed":
                raise ModerationError("This indicator was removed; it cannot be re-published here.")
            ind.status = "unverified"
            ind.verified_basis = None
            ind.verified_by = None
            ind.verified_at = None
        _event(db, ind.id, rep, moderator, "accepted" if action == "accept" else "unverified", reason)
        note = ("accepted as a report. The indicator is shown as reported, not verified.")
    elif action == "verify":
        if rep.status in ("rejected", "withdrawn"):
            raise ModerationError("This report was already closed.")
        if ind.status == "removed":
            raise ModerationError("This indicator was removed.")
        n = _preview_independent(db, ind, rep)
        has_primary = db.scalar(select(Evidence.id).where(Evidence.indicator_id == ind.id, Evidence.primary_by_moderator.is_(True)).limit(1)) is not None
        decision = evaluate_verification(n, has_primary, policy_of(settings))
        if not decision.allowed:
            raise ModerationError(f"Cannot verify: {decision.reason}.")
        rep.status = "accepted"
        was = ind.status
        ind.status = "verified"
        ind.verified_basis = decision.basis
        ind.verified_by = moderator.id
        ind.verified_at = utcnow()
        _event(db, ind.id, rep, moderator, "verified", f"{reason} [{decision.reason}]")
        note = "accepted and the indicator is now verified with evidence."
        recompute_indicator(db, ind, settings)
        if was != "verified":
            dispatch_new_verified(db, ind)
    elif action == "request_evidence":
        if rep.status in ("rejected", "withdrawn", "merged"):
            raise ModerationError("This report is already closed.")
        rep.status = "awaiting_evidence"
        rep.evidence_request = reason
        _event(db, ind.id, rep, moderator, "evidence_requested", reason)
        note = f"needs more information: {reason}"
    elif action == "reject":
        if rep.status in ("rejected", "withdrawn"):
            raise ModerationError("This report was already closed.")
        rep.status = "rejected"
        _event(db, ind.id, rep, moderator, "rejected", reason)
        note = "not accepted after review."
    elif action == "merge":
        target = db.get(Indicator, target_indicator_id) if target_indicator_id else None
        if target is None or target.id == ind.id or target.status == "removed":
            raise ModerationError("Choose a different, existing indicator to merge into.")
        old_id = ind.id
        rep.indicator_id = target.id
        rep.status = "merged"
        first = db.scalar(select(Report.id).where(Report.indicator_id == target.id, Report.id != rep.id).order_by(Report.id).limit(1))
        rep.duplicate_of_id = first
        for ev in db.scalars(select(Evidence).where(Evidence.report_id == rep.id)):
            ev.indicator_id = target.id
        db.flush()
        _event(db, target.id, rep, moderator, "merged", reason)
        _event(db, old_id, rep, moderator, "merged_away", reason)
        if target.status == "pending":
            target.status = "unverified"
        remaining = [r for r in db.scalars(select(Report).where(Report.indicator_id == old_id)) if r.status in LIVE]
        if not remaining:
            ind.status = "removed"
        recompute_indicator(db, ind, settings)
        ind = target
        note = "merged with other reports of the same indicator."
    elif action == "restrict_reporter":
        if not can(moderator.role, "restrict.reporter"):
            raise ModerationError("You cannot restrict accounts.")
        if reporter is None:
            raise ModerationError("This report has no account to restrict (anonymous).")
        if reporter.role in ("moderator", "platform_admin"):
            raise ModerationError("Staff accounts cannot be restricted here.")
        reporter.restricted = True
        reporter.restricted_reason = reason
        audit.record(db, moderator.id, "user.restricted", "user", reporter.id, reason)
        note = "Your account was restricted."
    else:  # attach_evidence
        if file_bytes is None:
            raise ModerationError("Attach an image.")
        try:
            sf = store_image(settings.storage_dir, file_bytes, settings.max_upload_bytes, settings.max_image_pixels)
        except UploadRejected as exc:
            raise ModerationError(str(exc)) from exc
        db.add(Evidence(report_id=rep.id, indicator_id=ind.id, storage_name=sf.storage_name, mime=sf.mime, size=sf.size, sha256=sf.sha256, primary_by_moderator=True, attached_by=moderator.id))
        _event(db, ind.id, rep, moderator, "evidence_attached", reason)
        note = "A moderator attached primary evidence."

    audit.record(db, moderator.id, f"moderation.{action}", "report", rep.id, reason, {"indicator_id": ind.id})
    recompute_indicator(db, ind, settings)
    if reporter and action in ("accept", "mark_unverified", "verify", "request_evidence", "reject", "merge"):
        notify_user(db, reporter, "status_change", f"Update on your report {rep.ref}", f"Your report {rep.ref} was {note}", respect_pref="on_status_change")
    db.flush()
    return rep
