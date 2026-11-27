"""Security primitives: Argon2id passwords, TOTP, CSRF tokens, API keys, field encryption."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

_ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)  # Argon2id (OWASP minimum profile)
API_KEY_PREFIX = "ssk_"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_problems(password: str) -> list[str]:
    problems = []
    if len(password) < 10:
        problems.append("at least 10 characters")
    if len(password) > 200:
        problems.append("at most 200 characters")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        problems.append("letters and at least one number")
    if password.lower() in {"password123", "1234567890", "qwerty12345", "password1234"}:
        problems.append("not a commonly used password")
    return problems


# ---- field encryption (TOTP secrets at rest) ----
def _fernet(secret_key: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(("field-enc:" + secret_key).encode()).digest())
    return Fernet(key)


def encrypt_field(secret_key: str, plain: str) -> str:
    return _fernet(secret_key).encrypt(plain.encode()).decode()


def decrypt_field(secret_key: str, token: str) -> str | None:
    try:
        return _fernet(secret_key).decrypt(token.encode()).decode()
    except InvalidToken:
        return None


# ---- TOTP ----
def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="ScamShield Africa")


def verify_totp(secret: str, code: str) -> bool:
    code = re.sub(r"\s", "", code or "")
    if not re.fullmatch(r"\d{6}", code):
        return False
    return bool(pyotp.TOTP(secret).verify(code, valid_window=1))


def new_recovery_codes(n: int = 8) -> list[str]:
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()


# ---- sessions and CSRF ----
def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_id(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_for(secret_key: str, binding: str) -> str:
    """CSRF token bound to the session (or the anonymous cookie id)."""
    return hmac.new(secret_key.encode(), ("csrf:" + binding).encode(), hashlib.sha256).hexdigest()


def csrf_valid(secret_key: str, binding: str, supplied: str | None) -> bool:
    if not binding or not supplied:
        return False
    return hmac.compare_digest(csrf_for(secret_key, binding), supplied)


def device_bucket(secret_key: str, ip: str, user_agent: str) -> str:
    """Salted hash of coarse network+client info. Raw IPs are never stored."""
    coarse = ".".join(ip.split(".")[:3]) if "." in ip else ip.rsplit(":", 2)[0]
    return hmac.new(secret_key.encode(), f"{coarse}|{user_agent[:60]}".encode(), hashlib.sha256).hexdigest()[:32]


# ---- API keys ----
def generate_api_key() -> tuple[str, str, str]:
    """Return (full_key, prefix, sha256 hash). The full key is shown once and never stored."""
    prefix = API_KEY_PREFIX + secrets.token_hex(4)
    full = prefix + "_" + secrets.token_urlsafe(30)
    return full, prefix, hashlib.sha256(full.encode()).hexdigest()


def split_api_key(full: str) -> str | None:
    m = re.fullmatch(r"(ssk_[0-9a-f]{8})_[A-Za-z0-9_\-]{20,}", full or "")
    return m.group(1) if m else None


def api_key_matches(full: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hashlib.sha256(full.encode()).hexdigest(), stored_hash)
