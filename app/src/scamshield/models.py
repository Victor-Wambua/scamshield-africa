"""ORM models. Schema is portable between SQLite and PostgreSQL (no vendor-specific types).

Every record that can be demonstration data carries an ``origin`` field, one of ORIGINS.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

ORIGINS = ("user-submitted", "synthetic test data", "mock integration", "officially published", "verified live")
ROLES = ("reporter", "contributor", "moderator", "org_analyst", "org_admin", "platform_admin")
INDICATOR_TYPES = ("phone", "url", "email", "wallet", "social", "payment_ref", "business", "message")
CATEGORIES = ("reversal", "phishing", "investment", "jobs", "tax", "impersonation", "prize", "other")


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(40), default="bank")
    status: Mapped[str] = mapped_column(String(20), default="approved")
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="reporter")
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"), nullable=True)
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_hashes: Mapped[list[str]] = mapped_column(JSON, default=list)
    restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    restricted_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    org: Mapped[Organisation | None] = relationship()


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 of cookie token
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    mfa_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_failures: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    user: Mapped[User] = relationship()


class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (UniqueConstraint("type", "norm_value", name="uq_indicator_type_value"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(20))
    norm_value: Mapped[str] = mapped_column(String(600), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|unverified|verified|removed
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)  # open correction request
    risk_category: Mapped[str] = mapped_column(String(20), default="other")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    independent_count: Mapped[int] = mapped_column(Integer, default=0)
    submission_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    first_reported: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_observed: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    verified_basis: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="community reports")
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_indicator", "indicator_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref: Mapped[str] = mapped_column(String(20), unique=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"))
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    device_bucket: Mapped[str] = mapped_column(String(64), default="")
    owning_org_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"), nullable=True)
    api_key_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    itype: Mapped[str] = mapped_column(String(20))
    raw_value: Mapped[str] = mapped_column(String(600))
    category: Mapped[str] = mapped_column(String(20), default="other")
    description: Mapped[str] = mapped_column(Text)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    amount_kes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    county: Mapped[str | None] = mapped_column(String(40), nullable=True)
    consent_privacy: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_share_partners: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    # received|in_review|awaiting_evidence|accepted|rejected|merged|withdrawn
    status: Mapped[str] = mapped_column(String(20), default="received")
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    counts_independent: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    shingles_sig: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    indicator: Mapped[Indicator] = relationship()


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"))
    storage_name: Mapped[str] = mapped_column(String(80), unique=True)
    mime: Mapped[str] = mapped_column(String(40))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    primary_by_moderator: Mapped[bool] = mapped_column(Boolean, default=False)
    attached_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReviewEvent(Base):
    """Public-safe review history of an indicator (moderator ids visible to staff only)."""

    __tablename__ = "review_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"), index=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Append-only, hash-chained. UPDATE/DELETE are blocked by ORM hooks and DB triggers."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    target_type: Mapped[str] = mapped_column(String(30), default="")
    target_id: Mapped[str] = mapped_column(String(40), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")


class Correction(Base):
    __tablename__ = "corrections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref: Mapped[str] = mapped_column(String(20), unique=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"), index=True)
    relationship_: Mapped[str] = mapped_column("relationship", String(30))
    explanation: Mapped[str] = mapped_column(Text)
    contact_email: Mapped[str] = mapped_column(String(254))
    urgent_legal: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|accepted|declined|removed
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    indicator: Mapped[Indicator] = relationship()


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(80))
    prefix: Mapped[str] = mapped_column(String(16), unique=True)
    key_hash: Mapped[str] = mapped_column(String(64))
    scopes: Mapped[str] = mapped_column(String(200))
    environment: Mapped[str] = mapped_column(String(10), default="test")
    rate_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ApiUsage(Base):
    __tablename__ = "api_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    endpoint: Mapped[str] = mapped_column(String(80))
    status: Mapped[int] = mapped_column(Integer)


class RateHit(Base):
    __tablename__ = "rate_hits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bucket: Mapped[str] = mapped_column(String(120), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    origin: Mapped[str] = mapped_column(String(40), default="user-submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CaseIndicator(Base):
    __tablename__ = "case_indicators"
    __table_args__ = (UniqueConstraint("case_id", "indicator_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"))


class CaseNote(Base):
    __tablename__ = "case_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(20))
    frequency: Mapped[str] = mapped_column(String(10), default="instant")  # instant|daily|weekly
    channel: Mapped[str] = mapped_column(String(10), default="email")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_digest_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NotificationPref(Base):
    __tablename__ = "notification_prefs"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    on_new_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    on_status_change: Mapped[bool] = mapped_column(Boolean, default=True)
    on_org_updates: Mapped[bool] = mapped_column(Boolean, default=False)
    frequency: Mapped[str] = mapped_column(String(10), default="instant")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MailOutbox(Base):
    """Sandbox mailer log. Nothing is delivered: no provider is connected (mock integration)."""

    __tablename__ = "mail_outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    to_addr: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(40), default="mock integration")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
