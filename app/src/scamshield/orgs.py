"""Institutional features: analytics, CSV export, API keys, threat intelligence."""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import audit, ratelimit
from .config import Settings
from .models import ApiKey, ApiUsage, Indicator, Report, User, utcnow
from .normalize import mask_value
from .reports import PUBLIC_STATUSES
from .rules import suppress_small
from .security import api_key_matches, generate_api_key, split_api_key
from .tenancy import TenantScope

SCOPES = ("lookup", "report", "intel", "analytics")
COUNTIES = ("Nairobi", "Mombasa", "Kisumu", "Nakuru", "Uasin Gishu", "Kiambu", "Machakos", "Kakamega", "Meru", "Nyeri", "Kajiado", "Other")


def analytics(scope: TenantScope, days: int = 30) -> dict[str, Any]:
    db = scope.db
    since = utcnow() - timedelta(days=days)
    reps = list(db.scalars(scope.reports().where(Report.created_at >= since)))
    by_cat = Counter(r.category for r in reps)
    by_type = Counter(r.itype for r in reps)
    by_status = Counter(r.status for r in reps)
    per_day: Counter[str] = Counter(r.created_at.date().isoformat() for r in reps)
    series = []
    for i in range(days):
        d = (since + timedelta(days=i + 1)).date().isoformat()
        series.append((d, per_day.get(d, 0)))
    counties = Counter(r.county or "Unknown" for r in reps)
    thr = scope_threshold()
    geo = [(c, suppress_small(n, thr)) for c, n in counties.most_common()]
    return {
        "days": days,
        "total": len(reps),
        "by_category": by_cat.most_common(),
        "by_type": by_type.most_common(),
        "by_status": by_status.most_common(),
        "series": series,
        "geo": geo,
        "suppression_threshold": thr,
        "open_cases": _open_cases(scope),
    }


def _open_cases(scope: TenantScope) -> int:
    return sum(1 for c in scope.db.scalars(scope.cases()) if c.status == "open")


def scope_threshold() -> int:
    from .config import get_settings

    return get_settings().county_suppression_threshold


def network_trends(db: Session, days: int = 30) -> dict[str, Any]:
    """Network-wide aggregate (no per-record data): verified indicators by category."""
    since = utcnow() - timedelta(days=days)
    rows = db.execute(select(Indicator.risk_category, func.count()).where(Indicator.status == "verified", Indicator.verified_at >= since).group_by(Indicator.risk_category)).all()
    return {"verified_by_category": sorted(((c, n) for c, n in rows), key=lambda x: -x[1])}


def _safe_cell(v: Any) -> Any:
    """Neutralise spreadsheet formula injection."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def export_csv(scope: TenantScope, days: int = 90) -> str:
    """CSV of the organisation's own reports. Never includes reporter identity or raw evidence."""
    since = utcnow() - timedelta(days=days)
    reps = list(scope.db.scalars(scope.reports().where(Report.created_at >= since).order_by(Report.id)))
    out = io.StringIO()
    if any(r.origin == "synthetic test data" for r in reps):
        out.write("# Synthetic demonstration data. Not real incidents.\n")
    w = csv.writer(out)
    w.writerow(["reference", "received", "type", "category", "county", "status", "indicator_id", "amount_kes", "origin"])
    for r in reps:
        w.writerow([_safe_cell(x) for x in [r.ref, r.created_at.date().isoformat(), r.itype, r.category, r.county or "", r.status, r.indicator_id, r.amount_kes if r.amount_kes is not None else "", r.origin]])
    return out.getvalue()


# ---------------- API keys ----------------
def create_key(scope: TenantScope, user: User, name: str, scopes: list[str], environment: str, settings: Settings) -> tuple[ApiKey, str]:
    name = name.strip()
    if not name or len(name) > 80:
        raise ValueError("Give the key a name (up to 80 characters).")
    bad = [s for s in scopes if s not in SCOPES]
    if bad or not scopes:
        raise ValueError("Choose at least one valid scope.")
    if environment != "test":
        raise ValueError("Only test keys are available until your organisation is approved for live use.")
    full, prefix, h = generate_api_key()
    key = ApiKey(org_id=scope.org_id, created_by=user.id, name=name, prefix=prefix, key_hash=h, scopes=",".join(sorted(set(scopes))), environment=environment, rate_per_minute=settings.api_rate_per_minute)
    scope.db.add(key)
    scope.db.flush()
    audit.record(scope.db, user.id, "apikey.created", "api_key", key.id, detail={"scopes": key.scopes})
    return key, full


class ApiAuthError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def authenticate_key(db: Session, presented: str | None) -> ApiKey:
    prefix = split_api_key(presented or "")
    if not prefix:
        raise ApiAuthError(401, "Missing or malformed API key.")
    key = db.scalar(select(ApiKey).where(ApiKey.prefix == prefix))
    if key is None or not api_key_matches(presented or "", key.key_hash):
        raise ApiAuthError(401, "Invalid API key.")
    if key.revoked_at is not None:
        raise ApiAuthError(401, "This API key was revoked.")
    return key


def check_rate(db: Session, key: ApiKey) -> ratelimit.RateResult:
    return ratelimit.hit(db, f"apikey:{key.id}", key.rate_per_minute, 60)


def log_usage(db: Session, key: ApiKey, endpoint: str, status: int) -> None:
    db.add(ApiUsage(key_id=key.id, endpoint=endpoint, status=status))
    key.last_used_at = utcnow()
    db.flush()


def usage_summary(scope: TenantScope, days: int = 7) -> dict[str, Any]:
    since = utcnow() - timedelta(days=days)
    key_ids = [k.id for k in scope.db.scalars(scope.keys())]
    rows = list(scope.db.scalars(select(ApiUsage).where(ApiUsage.key_id.in_(key_ids or [0]), ApiUsage.ts >= since)))
    return {
        "total": len(rows),
        "errors": sum(1 for r in rows if r.status >= 400),
        "throttled": sum(1 for r in rows if r.status == 429),
        "by_endpoint": Counter(r.endpoint for r in rows).most_common(),
    }


def threat_intel(db: Session, category: str | None = None, since_days: int = 30, limit: int = 200) -> list[dict[str, Any]]:
    """Verified indicators for authorised partners (exact values, no reporter data, no evidence)."""
    since = utcnow() - timedelta(days=since_days)
    stmt = select(Indicator).where(Indicator.status == "verified", Indicator.updated_at >= since)
    if category:
        stmt = stmt.where(Indicator.risk_category == category)
    out = []
    for ind in db.scalars(stmt.order_by(Indicator.verified_at.desc()).limit(limit)):
        out.append({"id": ind.id, "type": ind.type, "value": ind.norm_value if ind.type != "message" else mask_value("message", ind.norm_value), "category": ind.risk_category,
                    "independent_reports": ind.independent_count, "confidence": ind.confidence, "disputed": ind.flagged, "first_reported": ind.first_reported.date().isoformat(),
                    "last_observed": ind.last_observed.date().isoformat(), "origin": ind.origin})
    return out


__all__ = ["PUBLIC_STATUSES"]
