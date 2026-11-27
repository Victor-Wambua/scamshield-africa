"""Runtime configuration. All values come from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Settings object. Decision-driven policy values are configurable here (docs/DECISIONS.md)."""

    database_url: str = field(default_factory=lambda: os.environ.get("SS_DATABASE_URL", "sqlite:///./data/scamshield.db"))
    secret_key: str = field(default_factory=lambda: os.environ.get("SS_SECRET_KEY", "dev-only-insecure-secret-change-me"))
    storage_dir: Path = field(default_factory=lambda: Path(os.environ.get("SS_STORAGE_DIR", "./data/evidence")))
    environment: str = field(default_factory=lambda: os.environ.get("SS_ENV", "development"))
    cookie_secure: bool = field(default_factory=lambda: _bool("SS_COOKIE_SECURE", False))
    session_hours: int = field(default_factory=lambda: _int("SS_SESSION_HOURS", 12))
    # Decision 1: verification policy
    verify_min_independent: int = field(default_factory=lambda: _int("SS_VERIFY_MIN_INDEPENDENT", 3))
    verify_allow_moderator_evidence: bool = field(default_factory=lambda: _bool("SS_VERIFY_ALLOW_MOD_EVIDENCE", True))
    # Decision 4: correction SLA
    correction_sla_days: int = field(default_factory=lambda: _int("SS_CORRECTION_SLA_DAYS", 7))
    # Auth hardening
    max_failed_logins: int = field(default_factory=lambda: _int("SS_MAX_FAILED_LOGINS", 5))
    lockout_minutes: int = field(default_factory=lambda: _int("SS_LOCKOUT_MINUTES", 15))
    max_failed_mfa: int = field(default_factory=lambda: _int("SS_MAX_FAILED_MFA", 3))
    mfa_roles: tuple[str, ...] = ("moderator", "org_analyst", "org_admin", "platform_admin")
    # Rate limits (per window seconds)
    api_rate_per_minute: int = field(default_factory=lambda: _int("SS_API_RATE_PER_MINUTE", 60))
    report_rate_per_hour: int = field(default_factory=lambda: _int("SS_REPORT_RATE_PER_HOUR", 10))
    correction_rate_per_hour: int = field(default_factory=lambda: _int("SS_CORRECTION_RATE_PER_HOUR", 5))
    login_rate_per_15min: int = field(default_factory=lambda: _int("SS_LOGIN_RATE_PER_15MIN", 20))
    # Uploads
    max_upload_bytes: int = field(default_factory=lambda: _int("SS_MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
    max_uploads_per_report: int = field(default_factory=lambda: _int("SS_MAX_UPLOADS_PER_REPORT", 5))
    max_image_pixels: int = 25_000_000
    # Analytics privacy
    county_suppression_threshold: int = field(default_factory=lambda: _int("SS_COUNTY_SUPPRESSION", 5))
    # Optional LLM adapter (off by default; never called in tests)
    llm_enabled: bool = field(default_factory=lambda: _bool("SS_LLM_ENABLED", False))
    default_language: str = "en"
    mail_log_path: Path = field(default_factory=lambda: Path(os.environ.get("SS_MAIL_LOG", "./data/mail.log")))

    @property
    def is_production_like(self) -> bool:
        return self.environment in {"production", "staging"}

    def validate(self) -> None:
        """Refuse insecure defaults outside development."""
        if self.is_production_like and self.secret_key.startswith("dev-only"):
            raise RuntimeError("SS_SECRET_KEY must be set in staging/production")
        if self.is_production_like and not self.cookie_secure:
            raise RuntimeError("SS_COOKIE_SECURE must be true in staging/production")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(s: Settings | None) -> None:
    global _settings
    _settings = s
