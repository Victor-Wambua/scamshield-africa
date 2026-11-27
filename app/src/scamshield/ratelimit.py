"""Database-backed sliding-window rate limiter (works across workers, portable SQL)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .models import RateHit, utcnow


@dataclass
class RateResult:
    allowed: bool
    remaining: int
    retry_after: int


def hit(db: Session, bucket: str, limit: int, window_seconds: int) -> RateResult:
    """Record a hit and report whether it is within `limit` per window."""
    now = utcnow()
    since = now - timedelta(seconds=window_seconds)
    count = db.scalar(select(func.count()).select_from(RateHit).where(RateHit.bucket == bucket, RateHit.ts > since)) or 0
    if count >= limit:
        oldest = db.scalar(select(func.min(RateHit.ts)).where(RateHit.bucket == bucket, RateHit.ts > since))
        retry = max(1, int(window_seconds - (now - oldest).total_seconds())) if oldest else window_seconds
        return RateResult(False, 0, retry)
    db.add(RateHit(bucket=bucket, ts=now))
    db.flush()
    return RateResult(True, limit - count - 1, 0)


def purge(db: Session, older_than_seconds: int = 86400) -> int:
    res = db.execute(delete(RateHit).where(RateHit.ts < utcnow() - timedelta(seconds=older_than_seconds)))
    return int(getattr(res, "rowcount", 0) or 0)
