"""Indicator normalisation: the single definition of "same indicator" used for duplicate detection.

Phones -> E.164, URLs -> canonical host (punycode) + path, emails -> lower-case with punycode domain,
wallets -> case-preserving (EIP-55 style addresses lower-cased), social handles, payment references.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

import idna

TRACKING_PARAMS = ("utm_", "fbclid", "gclid", "mc_", "ref_src")
_PHONE_KE = re.compile(r"^(?:\+?254|0)([17]\d{8})$")
_PHONE_INTL = re.compile(r"^\+(\d{8,15})$")
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-']{1,64}@([A-Za-z0-9\-\.]+\.[A-Za-z]{2,}|xn--[A-Za-z0-9\-\.]+)$")
_WALLET = re.compile(r"^[A-Za-z0-9]{26,95}$")
_ETH = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HOST = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z0-9\-]{2,63}$")
_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_PAYREF = re.compile(r"^[A-Z0-9]{4,30}$")
_HANDLE = re.compile(r"^@?([A-Za-z0-9_.]{3,40})$")
URL_IN_TEXT = re.compile(r"(?i)\b((?:https?://)?(?:[a-z0-9\-]+\.)+[a-z]{2,}(?:/[^\s<>\"']*)?)")
PHONE_IN_TEXT = re.compile(r"(?<![\d])(?:\+?254|0)[\s\-]?[17](?:[\s\-]?\d){8}(?!\d)")


class InvalidIndicator(ValueError):
    """Raised when a value cannot be normalised for the declared type."""


def _host_to_ascii(host: str) -> str:
    host = host.strip(".").lower()
    try:
        host = idna.encode(host, uts46=True).decode("ascii")
    except idna.IDNAError as exc:
        raise InvalidIndicator("invalid host name") from exc
    return host.lower()


def normalize_phone(value: str) -> str:
    v = re.sub(r"[\s\-().]", "", value.strip())
    if v.startswith("00"):
        v = "+" + v[2:]
    m = _PHONE_KE.match(v)
    if m:
        return "+254" + m.group(1)
    m = _PHONE_INTL.match(v)
    if m:
        return "+" + m.group(1)
    raise InvalidIndicator("not a valid phone number")


def normalize_url(value: str) -> str:
    v = value.strip()
    if not v or " " in v:
        raise InvalidIndicator("not a valid link")
    if "://" not in v:
        v = "http://" + v
    try:
        parts = urlsplit(v)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise InvalidIndicator("not a valid link") from exc
    if parts.scheme.lower() not in ("http", "https") or not host:
        raise InvalidIndicator("not a valid link")
    host = _host_to_ascii(host)
    if not (_IPV4.match(host) or _HOST.match(host)):
        raise InvalidIndicator("not a valid link")
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parts.path or "")
    if path == "/":
        path = ""
    path = path.rstrip("/") if len(path) > 1 else path
    q = sorted((k, val) for k, val in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith(TRACKING_PARAMS))
    out = host
    if port and port not in (80, 443):
        out += f":{port}"
    out += path
    if q:
        out += "?" + urlencode(q)
    return out


def normalize_email(value: str) -> str:
    v = value.strip()
    m = _EMAIL.match(v)
    if not m:
        raise InvalidIndicator("not a valid email address")
    local, _, domain = v.rpartition("@")
    return f"{local.lower()}@{_host_to_ascii(domain)}"


def normalize_wallet(value: str) -> str:
    v = re.sub(r"\s", "", value)
    if _ETH.match(v):
        return v.lower()
    if not _WALLET.match(v):
        raise InvalidIndicator("a wallet address needs at least 26 letters and digits")
    return v


def normalize_social(value: str) -> str:
    v = value.strip()
    if "/" in v or ("." in v and not v.startswith("@") and " " not in v):
        try:
            return normalize_url(v)
        except InvalidIndicator:
            pass
    m = _HANDLE.match(v)
    if not m:
        raise InvalidIndicator("not a valid social account")
    return "@" + m.group(1).lower()


def normalize_payment_ref(value: str) -> str:
    v = re.sub(r"[\s\-]", "", value).upper()
    if not _PAYREF.match(v):
        raise InvalidIndicator("a payment reference has 4 to 30 letters and digits")
    return v


def normalize_business(value: str) -> str:
    v = re.sub(r"\s+", " ", value.strip()).casefold()
    if len(v) < 3 or len(v) > 120:
        raise InvalidIndicator("a business name has 3 to 120 characters")
    return v


def normalize_message(value: str) -> str:
    """Message identity: digest of the text with URLs, numbers and spacing neutralised."""
    return "msg:" + hashlib.sha256(canonical_text(value).encode()).hexdigest()[:40]


def canonical_text(value: str) -> str:
    t = value.casefold()
    t = URL_IN_TEXT.sub(" <url> ", t)
    t = re.sub(r"\d+", "0", t)
    return re.sub(r"\s+", " ", t).strip()


_NORMALISERS = {
    "phone": normalize_phone,
    "url": normalize_url,
    "email": normalize_email,
    "wallet": normalize_wallet,
    "social": normalize_social,
    "payment_ref": normalize_payment_ref,
    "business": normalize_business,
    "message": normalize_message,
}


def normalize(itype: str, value: str) -> str:
    fn = _NORMALISERS.get(itype)
    if fn is None:
        raise InvalidIndicator("unknown indicator type")
    return fn(value)


def detect_type(value: str) -> str | None:
    """Best-effort type guess for the public search box."""
    v = value.strip()
    for itype in ("phone", "email", "wallet", "url"):
        try:
            normalize(itype, v)
        except InvalidIndicator:
            continue
        return itype
    return None


def extract_urls(text: str) -> list[str]:
    seen: list[str] = []
    for m in URL_IN_TEXT.finditer(text):
        raw = m.group(1).rstrip(".,);]")
        try:
            n = normalize_url(raw)
        except InvalidIndicator:
            continue
        if n not in seen:
            seen.append(n)
    return seen


def extract_phones(text: str) -> list[str]:
    seen: list[str] = []
    for m in PHONE_IN_TEXT.finditer(text):
        try:
            n = normalize_phone(m.group(0))
        except InvalidIndicator:
            continue
        if n not in seen:
            seen.append(n)
    return seen


def mask_value(itype: str, norm: str) -> str:
    """Partial masking for public lists (Decision 3). Exact-match search can show the full value."""
    if itype == "phone":
        return norm[:5] + "•• ••• " + norm[-3:] if norm.startswith("+254") else norm[:4] + "•••" + norm[-3:]
    if itype == "email":
        local, _, domain = norm.partition("@")
        return local[:1] + "•••@" + domain
    if itype == "wallet":
        return norm[:6] + "…" + norm[-4:]
    if itype in ("url",):
        host, sep, _rest = norm.partition("/")
        return host + ("/…" if sep else "")
    if itype == "message":
        return "Message pattern"
    return norm[:3] + "•••"
