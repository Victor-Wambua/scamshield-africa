"""Notifications: in-app + sandbox email, alert subscriptions, digest job."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import mailer
from .models import AlertSubscription, Indicator, Notification, NotificationPref, User, utcnow
from .normalize import mask_value


def notify_user(db: Session, user: User, kind: str, subject: str, body: str, *, respect_pref: str | None = None) -> bool:
    if respect_pref:
        pref = db.get(NotificationPref, user.id)
        if pref is not None and not getattr(pref, respect_pref):
            return False
    db.add(Notification(user_id=user.id, kind=kind, subject=subject[:200], body=body))
    mailer.send(db, user.email, subject, body)
    db.flush()
    return True


def _line(ind: Indicator) -> str:
    return f"- {ind.type} {mask_value(ind.type, ind.norm_value)} ({ind.risk_category}), {ind.independent_count} independent report(s)"


def dispatch_new_verified(db: Session, ind: Indicator) -> int:
    """Instant alerts for subscriptions matching the indicator's category. Returns messages sent."""
    sent = 0
    subs = db.scalars(select(AlertSubscription).where(AlertSubscription.enabled.is_(True), AlertSubscription.category == ind.risk_category, AlertSubscription.frequency == "instant"))
    for sub in subs:
        user = db.get(User, sub.user_id)
        if user is None or user.restricted or user.deleted:
            continue
        notify_user(db, user, "new_verified", f"New verified {ind.risk_category} warning", "A new indicator was verified with evidence:\n" + _line(ind))
        sent += 1
    return sent


def run_digest(db: Session, now: datetime | None = None) -> int:
    """Send daily/weekly digests. Idempotent: advances last_digest_at per subscription."""
    now = now or utcnow()
    due: dict[int, list[AlertSubscription]] = defaultdict(list)
    for sub in db.scalars(select(AlertSubscription).where(AlertSubscription.enabled.is_(True), AlertSubscription.frequency.in_(("daily", "weekly")))):
        gap = timedelta(days=1 if sub.frequency == "daily" else 7)
        if sub.last_digest_at is None or now - sub.last_digest_at >= gap:
            due[sub.user_id].append(sub)
    sent = 0
    for uid, subs in due.items():
        user = db.get(User, uid)
        lines: list[str] = []
        for sub in subs:
            since = sub.last_digest_at or (now - timedelta(days=1 if sub.frequency == "daily" else 7))
            inds = db.scalars(select(Indicator).where(Indicator.status == "verified", Indicator.risk_category == sub.category, Indicator.verified_at > since, Indicator.verified_at <= now))
            lines += [_line(i) for i in inds]
            sub.last_digest_at = now
        if user and lines and not user.restricted and not user.deleted:
            notify_user(db, user, "digest", "ScamShield digest: new verified warnings", "\n".join(sorted(set(lines))))
            sent += 1
    db.flush()
    return sent
