"""Accounts, sessions, lockout and TOTP MFA."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from . import audit
from .config import Settings
from .models import NotificationPref, PasswordReset, Session, User, utcnow
from . import mailer
from .normalize import InvalidIndicator, normalize
from .security import (
    decrypt_field, encrypt_field, hash_password, hash_recovery_code, new_recovery_codes, new_token,
    new_totp_secret, password_problems, token_id, verify_password, verify_totp,
)

_DUMMY_HASH = hash_password("not-a-real-password-1")


class AccountError(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def register(db: DbSession, email: str, password: str, display_name: str, accepted_terms: bool, *, role: str = "reporter", org_id: int | None = None, origin: str = "user-submitted") -> User:
    errors: dict[str, str] = {}
    try:
        email_n = normalize("email", email)
    except InvalidIndicator:
        errors["email"] = "Enter a valid email address."
        email_n = ""
    probs = password_problems(password)
    if probs:
        errors["password"] = "Password needs " + ", ".join(probs) + "."
    if not accepted_terms:
        errors["terms"] = "Please accept the terms and privacy notice."
    if not errors and db.scalar(select(User.id).where(User.email == email_n)):
        errors["email"] = "An account with this email already exists."
    if errors:
        raise AccountError(errors)
    u = User(email=email_n, display_name=display_name.strip()[:120], password_hash=hash_password(password), role=role, org_id=org_id, origin=origin)
    db.add(u)
    db.flush()
    db.add(NotificationPref(user_id=u.id))
    audit.record(db, u.id, "user.registered", "user", u.id, detail={"role": role})
    return u


class LoginFailed(Exception):
    pass


class LockedOut(Exception):
    pass


def authenticate(db: DbSession, settings: Settings, email: str, password: str) -> User:
    try:
        email_n = normalize("email", email)
    except InvalidIndicator:
        email_n = email.strip().lower()
    u = db.scalar(select(User).where(User.email == email_n))
    now = utcnow()
    if u is None or u.deleted:
        verify_password(_DUMMY_HASH, password)  # constant-ish time
        raise LoginFailed("Email or password is not correct.")
    if u.locked_until and u.locked_until > now:
        raise LockedOut("Too many failed attempts. Try again later.")
    if not verify_password(u.password_hash, password):
        u.failed_logins += 1
        if u.failed_logins >= settings.max_failed_logins:
            u.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            u.failed_logins = 0
            audit.record(db, u.id, "auth.locked", "user", u.id)
        db.flush()
        raise LoginFailed("Email or password is not correct.")
    u.failed_logins = 0
    u.locked_until = None
    return u


def needs_mfa(settings: Settings, user: User) -> bool:
    return user.role in settings.mfa_roles


def create_session(db: DbSession, settings: Settings, user: User) -> str:
    token = new_token()
    mfa_ok = not needs_mfa(settings, user)
    db.add(Session(id=token_id(token), user_id=user.id, mfa_passed=mfa_ok, expires_at=utcnow() + timedelta(hours=settings.session_hours)))
    audit.record(db, user.id, "auth.login", "user", user.id)
    db.flush()
    return token


def session_for(db: DbSession, token: str | None) -> Session | None:
    if not token:
        return None
    s = db.get(Session, token_id(token))
    if s is None or s.expires_at < utcnow() or s.user.deleted:
        return None
    return s


def end_session(db: DbSession, token: str | None) -> None:
    if token:
        s = db.get(Session, token_id(token))
        if s:
            db.delete(s)
            db.flush()


def begin_mfa_setup(settings: Settings, user: User) -> str:
    secret = new_totp_secret()
    user.totp_secret_enc = encrypt_field(settings.secret_key, secret)
    user.totp_enabled = False
    return secret


def current_secret(settings: Settings, user: User) -> str | None:
    return decrypt_field(settings.secret_key, user.totp_secret_enc) if user.totp_secret_enc else None


def confirm_mfa_setup(db: DbSession, settings: Settings, user: User, session: Session, code: str) -> list[str]:
    secret = current_secret(settings, user)
    if not secret or not verify_totp(secret, code):
        raise AccountError({"code": "That code is not correct."})
    codes = new_recovery_codes()
    user.recovery_hashes = [hash_recovery_code(c) for c in codes]
    user.totp_enabled = True
    session.mfa_passed = True
    audit.record(db, user.id, "mfa.enrolled", "user", user.id)
    return codes


def verify_mfa(db: DbSession, settings: Settings, user: User, session: Session, code: str) -> None:
    if session.mfa_failures >= settings.max_failed_mfa:
        raise LockedOut("Too many incorrect codes. Sign in again.")
    secret = current_secret(settings, user)
    ok = bool(secret) and verify_totp(secret or "", code)
    if not ok:
        h = hash_recovery_code(code)
        if h in (user.recovery_hashes or []):
            user.recovery_hashes = [x for x in user.recovery_hashes if x != h]
            audit.record(db, user.id, "mfa.recovery_used", "user", user.id)
            ok = True
    if not ok:
        session.mfa_failures += 1
        db.flush()
        raise LoginFailed("That code is not correct.")
    session.mfa_passed = True
    db.flush()


def start_password_reset(db: DbSession, email: str) -> str | None:
    """Create a one-hour reset token and mail it (sandbox). Returns the token for tests; callers must not reveal it."""
    try:
        email_n = normalize("email", email)
    except InvalidIndicator:
        return None
    u = db.scalar(select(User).where(User.email == email_n, User.deleted.is_(False)))
    if u is None:
        return None
    token = new_token()
    db.add(PasswordReset(user_id=u.id, token_hash=token_id(token), expires_at=utcnow() + timedelta(hours=1)))
    mailer.send(db, u.email, "Reset your ScamShield password", f"Use this link within one hour: /reset/{token}")
    audit.record(db, u.id, "auth.reset_requested", "user", u.id)
    return token


def reset_password(db: DbSession, token: str, new_password: str) -> User:
    pr = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == token_id(token)))
    if pr is None or pr.used_at is not None or pr.expires_at < utcnow():
        raise AccountError({"token": "This reset link is invalid or has expired."})
    probs = password_problems(new_password)
    if probs:
        raise AccountError({"password": "Password needs " + ", ".join(probs) + "."})
    u = db.get(User, pr.user_id)
    assert u is not None
    u.password_hash = hash_password(new_password)
    u.failed_logins = 0
    u.locked_until = None
    pr.used_at = utcnow()
    for s in db.scalars(select(Session).where(Session.user_id == u.id)):
        db.delete(s)
    audit.record(db, u.id, "auth.password_reset", "user", u.id)
    db.flush()
    return u


def delete_account(db: DbSession, user: User, reason: str) -> None:
    """Anonymise the account; reports stay (without contact data) so independence counts stay correct."""
    from .models import Report

    for r in db.scalars(select(Report).where(Report.reporter_id == user.id)):
        r.contact_email = None
        r.consent_contact = False
    for s in db.scalars(select(Session).where(Session.user_id == user.id)):
        db.delete(s)
    user.email = f"deleted-{user.id}@invalid.example"
    user.display_name = ""
    user.password_hash = hash_password(new_token())
    user.deleted = True
    user.totp_secret_enc = None
    user.recovery_hashes = []
    audit.record(db, user.id, "user.deleted", "user", user.id, reason)
    db.flush()
