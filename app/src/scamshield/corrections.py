"""Correction / challenge workflow (Decision 4): immediate acknowledgement, 7-day target, urgent legal path."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit, mailer
from .config import Settings
from .models import Correction, Evidence, Indicator, Report, ReviewEvent, User, utcnow
from .normalize import InvalidIndicator, normalize
from .notify import notify_user
from .permissions import can
from .reports import PUBLIC_STATUSES, next_ref, recompute_indicator
from .rules import correction_due, correction_overdue

RELATIONSHIPS = ("owner", "representative", "affected", "researcher", "other")


class CorrectionInvalid(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


class CorrectionError(Exception):
    pass


def submit_correction(
    db: Session, settings: Settings, indicator_id: int, relationship: str, explanation: str, contact_email: str, acknowledged: bool, urgent_legal: bool = False
) -> Correction:
    errors: dict[str, str] = {}
    ind = db.get(Indicator, indicator_id)
    if ind is None or ind.status not in PUBLIC_STATUSES:
        raise CorrectionInvalid({"indicator": "That record is not available."})
    if relationship not in RELATIONSHIPS:
        errors["relationship"] = "Choose how you are connected to this record."
    if len((explanation or "").strip()) < 20:
        errors["explanation"] = "Explain what is wrong in at least 20 characters."
    try:
        email = normalize("email", contact_email or "")
    except InvalidIndicator:
        errors["contact_email"] = "Enter a valid email address."
        email = ""
    if not acknowledged:
        errors["acknowledged"] = "Please confirm the statement."
    if errors:
        raise CorrectionInvalid(errors)
    now = utcnow()
    c = Correction(
        ref="C-PENDING", indicator_id=ind.id, relationship_=relationship, explanation=explanation.strip(), contact_email=email,
        urgent_legal=urgent_legal, acknowledged_at=now, due_at=correction_due(now, settings.correction_sla_days, urgent_legal), origin="user-submitted",
    )
    db.add(c)
    db.flush()
    c.ref = f"C-{c.id:04d}"
    ind.flagged = True
    db.add(ReviewEvent(indicator_id=ind.id, action="correction_requested", reason=""))
    mailer.send(db, email, f"Correction request {c.ref} received", f"We received your request {c.ref}. We aim to decide within {1 if urgent_legal else settings.correction_sla_days} day(s). The record is marked as disputed while we review.")
    audit.record(db, None, "correction.submitted", "correction", c.id, detail={"indicator_id": ind.id, "urgent_legal": urgent_legal})
    if urgent_legal:
        for admin in db.scalars(select(User).where(User.role == "platform_admin", User.deleted.is_(False))):
            notify_user(db, admin, "urgent_legal", f"Urgent legal correction {c.ref}", f"Indicator #{ind.id} has an urgent legal correction request that needs a platform administrator decision.")
        audit.record(db, None, "correction.urgent_flagged", "correction", c.id)
    recompute_indicator(db, ind, settings)
    return c


def decide_correction(db: Session, settings: Settings, actor: User, correction_id: int, decision: str, reason: str) -> Correction:
    if not can(actor.role, "corrections.handle"):
        raise CorrectionError("You do not have permission to handle corrections.")
    reason = (reason or "").strip()
    if len(reason) < 8:
        raise CorrectionError("A reason of at least 8 characters is required.")
    c = db.get(Correction, correction_id)
    if c is None:
        raise CorrectionError("Correction not found.")
    if c.status != "open":
        raise CorrectionError("This correction was already decided.")
    ind = db.get(Indicator, c.indicator_id)
    assert ind is not None
    if decision == "remove":
        if not can(actor.role, "corrections.remove"):
            raise CorrectionError("Removing data needs a platform administrator.")
    elif decision in ("accept", "decline"):
        if ind.verified_by == actor.id and actor.role != "platform_admin":
            raise CorrectionError("A different moderator must decide corrections on records you verified.")
    else:
        raise CorrectionError("Unknown decision.")
    now = utcnow()
    c.decided_by, c.decided_at, c.decision_reason = actor.id, now, reason
    if decision == "accept":
        c.status = "accepted"
        if ind.status == "verified":
            ind.status = "unverified"
            ind.verified_basis = ind.verified_by = ind.verified_at = None
        db.add(ReviewEvent(indicator_id=ind.id, actor_id=actor.id, action="correction_accepted", reason=reason))
    elif decision == "decline":
        c.status = "declined"
        db.add(ReviewEvent(indicator_id=ind.id, actor_id=actor.id, action="correction_declined", reason=reason))
    else:
        c.status = "removed"
        ind.status = "removed"
        ind.verified_basis = ind.verified_by = ind.verified_at = None
        db.add(ReviewEvent(indicator_id=ind.id, actor_id=actor.id, action="removed", reason=reason))
        for ev in db.scalars(select(Evidence).where(Evidence.indicator_id == ind.id)):
            _delete_file(settings, ev)
            db.delete(ev)
        for rep in db.scalars(select(Report).where(Report.indicator_id == ind.id)):
            rep.message_text, rep.raw_value, rep.description, rep.analysis, rep.shingles_sig = None, "[removed]", "[removed after correction decision]", None, None
    still_open = db.scalar(select(Correction.id).where(Correction.indicator_id == ind.id, Correction.status == "open", Correction.id != c.id))
    ind.flagged = still_open is not None
    audit.record(db, actor.id, f"correction.{decision}", "correction", c.id, reason, {"indicator_id": ind.id})
    mailer.send(db, c.contact_email, f"Decision on {c.ref}", f"Your request {c.ref} was decided: {c.status}. Reason: {reason}")
    recompute_indicator(db, ind, settings)
    return c


def _delete_file(settings: Settings, ev: Evidence) -> None:
    from .uploads import path_for

    p = path_for(settings.storage_dir, ev.storage_name)
    if p is not None:
        p.unlink(missing_ok=True)


def queue(db: Session, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or utcnow()
    out = []
    for c in db.scalars(select(Correction).order_by(Correction.status, Correction.due_at)):
        out.append({"c": c, "overdue": correction_overdue(c.due_at, now, c.status)})
    return out
