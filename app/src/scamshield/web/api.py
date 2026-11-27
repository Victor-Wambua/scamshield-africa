"""Public/partner REST API v1 (OpenAPI at /docs). Authenticated with scoped, hashed, rate-limited keys."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import orgs
from ..models import ApiKey
from ..reports import ReportInvalid, SubmitInput, exact_lookup, public_view, submit_report
from ..tenancy import TenantScope, TenantViolation

router = APIRouter(prefix="/api/v1", tags=["api"])


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None, details: dict[str, str] | None = None) -> None:
        self.status, self.code, self.message, self.headers, self.details = status, code, message, headers or {}, details


def error_response(exc: ApiError) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": exc.code, "message": exc.message}}
    if exc.details:
        body["error"]["details"] = exc.details
    return JSONResponse(body, status_code=exc.status, headers=exc.headers)


class Caller:
    def __init__(self, db: Session, key: ApiKey, endpoint: str, request: Request) -> None:
        self.db, self.key, self.endpoint, self.request = db, key, endpoint, request
        self.remaining = 0

    def done(self, status: int) -> None:
        orgs.log_usage(self.db, self.key, self.endpoint, status)
        self.db.commit()


def caller_for(scope_name: str):  # type: ignore[no-untyped-def]
    def dep(request: Request, authorization: Annotated[str | None, Header()] = None, x_api_key: Annotated[str | None, Header()] = None):  # type: ignore[no-untyped-def]
        db = request.app.state.database.factory()
        try:
            presented = x_api_key or (authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None)
            endpoint = f"{request.method} {request.scope['route'].path if 'route' in request.scope else request.url.path}"
            try:
                key = orgs.authenticate_key(db, presented)
            except orgs.ApiAuthError as exc:
                raise ApiError(exc.status, "unauthorized", exc.message, {"WWW-Authenticate": "Bearer"}) from exc
            c = Caller(db, key, endpoint, request)
            rate = orgs.check_rate(db, key)
            if not rate.allowed:
                c.done(429)
                raise ApiError(429, "rate_limited", "Rate limit exceeded.", {"Retry-After": str(rate.retry_after), "X-RateLimit-Limit": str(key.rate_per_minute), "X-RateLimit-Remaining": "0"})
            c.remaining = rate.remaining
            if scope_name not in key.scopes.split(","):
                c.done(403)
                raise ApiError(403, "forbidden", f"This key lacks the '{scope_name}' scope.")
            yield c
        finally:
            db.close()

    return dep


class LookupResponse(BaseModel):
    found: bool
    indicator: dict[str, Any] | None = None
    notice: str = "Not found does not mean safe."


class ReportIn(BaseModel):
    type: str = Field(examples=["phone"], description="phone|url|email|wallet|social|payment_ref|business|message")
    value: str = Field(max_length=600, examples=["+254700000001"])
    description: str = Field(min_length=20, max_length=2000)
    category: str = "other"
    message_text: str | None = Field(default=None, max_length=5000)
    incident_date: datetime | None = None
    amount_kes: int | None = Field(default=None, ge=0)
    county: str | None = None
    consent_privacy: bool = False
    consent_truth: bool = False


class ReportOut(BaseModel):
    reference: str
    status: str
    is_duplicate: bool
    counts_as_independent: bool


def _hdr(c: Caller) -> dict[str, str]:
    return {"X-RateLimit-Limit": str(c.key.rate_per_minute), "X-RateLimit-Remaining": str(c.remaining)}


@router.get("/indicators/lookup", response_model=LookupResponse, summary="Look up an indicator by exact value")
def lookup(value: Annotated[str, Query(max_length=600)], type: str | None = None, c: Caller = Depends(caller_for("lookup"))) -> JSONResponse:  # noqa: B008
    inds = exact_lookup(c.db, value, type)
    body = {"found": bool(inds), "indicator": public_view(inds[0], exact=True) if inds else None, "notice": "Not found does not mean safe."}
    c.done(200)
    return JSONResponse(body, headers=_hdr(c))


@router.post("/reports", response_model=ReportOut, status_code=201, summary="Submit a report on behalf of your organisation")
def create_report(body: ReportIn, c: Caller = Depends(caller_for("report"))) -> JSONResponse:  # noqa: B008
    inp = SubmitInput(itype=body.type, value=body.value, description=body.description, category=body.category, message_text=body.message_text, incident_date=body.incident_date,
                      amount_kes=body.amount_kes, county=body.county, consent_privacy=body.consent_privacy, consent_truth=body.consent_truth)
    try:
        res = submit_report(c.db, c.request.app.state.settings, inp, reporter=None, bucket=f"key:{c.key.id}", owning_org_id=c.key.org_id, api_key_id=c.key.id)
    except ReportInvalid as exc:
        c.db.rollback()
        c.done(422)
        raise ApiError(422, "invalid_report", "The report is invalid.", details=exc.errors) from exc
    c.db.commit()
    c.done(201)
    return JSONResponse({"reference": res.report.ref, "status": res.report.status, "is_duplicate": res.is_duplicate, "counts_as_independent": res.independent}, status_code=201, headers=_hdr(c))


@router.get("/reports/{ref}/status", summary="Status of a report submitted by your organisation")
def report_status(ref: str, c: Caller = Depends(caller_for("report"))) -> JSONResponse:  # noqa: B008
    scope = TenantScope(c.db, c.key.org_id)
    from sqlalchemy import select

    from ..models import Report

    rep = c.db.scalar(scope.reports().where(Report.ref == ref))
    if rep is None:
        c.done(404)
        raise ApiError(404, "not_found", "No such report for your organisation.")
    ind = rep.indicator
    body = {"reference": rep.ref, "status": rep.status, "indicator_status": ind.status if ind.status in ("verified", "unverified") else "not_published", "received": rep.created_at.isoformat()}
    c.done(200)
    _ = select
    return JSONResponse(body, headers=_hdr(c))


@router.get("/threat-intel", summary="Verified indicators (partners only)")
def threat_intel(category: str | None = None, since_days: Annotated[int, Query(ge=1, le=365)] = 30, c: Caller = Depends(caller_for("intel"))) -> JSONResponse:  # noqa: B008
    items = orgs.threat_intel(c.db, category, since_days)
    c.done(200)
    return JSONResponse({"count": len(items), "items": items}, headers=_hdr(c))


@router.get("/org/analytics", summary="Analytics for your organisation's own reports")
def org_analytics(days: Annotated[int, Query(ge=1, le=90)] = 30, c: Caller = Depends(caller_for("analytics"))) -> JSONResponse:  # noqa: B008
    try:
        data = orgs.analytics(TenantScope(c.db, c.key.org_id), days)
    except TenantViolation as exc:  # pragma: no cover - keys always have an org
        raise ApiError(403, "forbidden", "No organisation.") from exc
    data.pop("series", None)
    c.done(200)
    return JSONResponse(data, headers=_hdr(c))
