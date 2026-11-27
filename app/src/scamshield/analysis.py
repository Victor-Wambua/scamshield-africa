"""Transparent rule + similarity scam-signal analysis.

Returns {label, confidence, reasons[], matched_prior_reports[]}. It never states that something *is* a
scam: labels describe warning signs only. "confidence" is confidence in the ANALYSIS (how much evidence
the rules saw), not a probability of fraud.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .llm_adapter import LLMAdapter
from .normalize import extract_phones, extract_urls

ENGINE_VERSION = "rules-1.0"
LABELS = ("several_warning_signs", "some_warning_signs", "few_warning_signs")
# Thresholds tuned on the DEV split of the synthetic set only (evaluation/README.md)
T_SEVERAL = 0.60
T_SOME = 0.25

OFFICIAL_DOMAINS = {
    "safaricom": ("safaricom.co.ke", "safaricom.com"),
    "mpesa": ("safaricom.co.ke", "m-pesa.com"),
    "kcb": ("kcbgroup.com", "kcb.co.ke"),
    "equity": ("equitybank.co.ke", "equitygroupholdings.com"),
    "ncba": ("ncbagroup.com",),
    "kra": ("kra.go.ke",),
    "ecitizen": ("ecitizen.go.ke",),
    "nssf": ("nssf.go.ke",),
    "airtel": ("airtel.co.ke", "africa.airtel.com"),
    "absa": ("absa.co.ke",),
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.ly", "cutt.ly", "rb.gy", "is.gd", "shorturl.at", "tiny.cc", "ow.ly"}
RISKY_TLDS = (".xyz", ".top", ".click", ".icu", ".cfd", ".sbs", ".buzz", ".site", ".online", ".vip", ".cc", ".tk")
ORG_WORDS = re.compile(
    r"(?i)\b(safaricom|m-?pesa|kcb|equity|co-?op(?:erative)? bank|ncba|kra|ecitizen|e-citizen|nssf|sha\b|airtel|absa|stanbic|dtb|central bank|huduma|ntsa)\b"
)

SIGNALS: dict[str, tuple[float, re.Pattern[str], str]] = {
    "urgency": (
        0.20,
        re.compile(r"(?i)\b(urgent(ly)?|immediately|within \d+ ?(hours?|hrs|minutes|mins)|last chance|act (now|fast)|expires?|haraka|sasa hivi|mara moja|today only)\b"),
        "Pressure to act quickly. Genuine organisations rarely demand instant action.",
    ),
    "payment_request": (
        0.30,
        re.compile(r"(?i)\b(send (me )?(ksh|kes|money|cash)|pay (a |the )?(fee|ksh|kes)|deposit (ksh|kes|first)|till (number|no)|paybill|tuma (pesa|ksh)|lipa)\b"),
        "Asks you to send or pay money.",
    ),
    "reversal_story": (
        0.40,
        re.compile(r"(?i)(by mistake|wrong number|erroneous(ly)?|kimakosa|kwa makosa|reverse (the|my|this) (money|transaction|payment)|rudisha (pesa|hizo))"),
        "Describes a mistaken transfer and asks for the money back. This is a common reversal story.",
    ),
    "prize": (
        0.40,
        re.compile(r"(?i)\b(you (have )?won|congratulations|winner|lottery|jackpot|umeshinda|zawadi|free (gift|airtime|data))\b"),
        "Claims you won a prize you did not enter for.",
    ),
    "credential_request": (
        0.45,
        re.compile(r"(?i)\b(pin|password|otp|one[- ]time (code|password)|verification code|cvv|confirm your (account|details|identity)|id number|namba ya siri|thibitisha akaunti)\b"),
        "Asks for a PIN, password, code or identity details. Organisations should not ask for these by message.",
    ),
    "advance_fee": (
        0.45,
        re.compile(r"(?i)\b(processing|registration|clearance|release|handling|delivery|activation) fee\b|ada ya (usajili|kusafirisha)"),
        "Asks for a fee before giving something. This is typical of advance-fee schemes.",
    ),
    "investment": (
        0.45,
        re.compile(r"(?i)(guaranteed (returns?|profit)|double your (money|investment)|daily (profit|returns?)|\d+ ?% (returns?|profit|daily|weekly)|no risk|forex signals|crypto signals|invest (ksh|kes) ?[\d,]+)"),
        "Promises high or guaranteed investment returns.",
    ),
    "threat": (
        0.30,
        re.compile(r"(?i)(account (will be|has been) (suspended|blocked|closed|deactivated)|legal action|you will be arrested|imefungwa|akaunti yako itafungwa)"),
        "Threatens loss of an account or legal trouble to force action.",
    ),
    "job_offer": (
        0.20,
        re.compile(r"(?i)(job offer|we are hiring|work from home|earn (ksh|kes) ?[\d,]+ (daily|per day|weekly)|ajira)"),
        "Offers work or easy earnings. Check carefully before paying or sharing documents.",
    ),
    "off_platform": (
        0.10,
        re.compile(r"(?i)(whatsapp|telegram|dm me|inbox me|contact (me|us) on)"),
        "Moves the conversation to a private chat.",
    ),
}


@dataclass
class Prior:
    indicator_id: int
    type: str
    value_masked: str
    status: str
    independent_reports: int
    match: str  # exact | similar
    similarity: float = 1.0


@dataclass
class AnalysisContext:
    """Lookups injected by the caller so the engine stays pure and testable."""

    lookup_indicator: Callable[[str, str], Prior | None] = lambda t, v: None
    similar_messages: Callable[[str], list[Prior]] = lambda text: []


@dataclass
class Highlight:
    start: int
    end: int
    signal: str


@dataclass
class AnalysisResult:
    label: str
    confidence: float
    score: float
    reasons: list[dict[str, str]] = field(default_factory=list)
    matched_prior_reports: list[dict[str, Any]] = field(default_factory=list)
    highlights: list[dict[str, Any]] = field(default_factory=list)
    engine: str = ENGINE_VERSION
    model_assisted: bool = False
    disclaimer: str = (
        "This is an automated check of warning signs. It is not proof that anything is or is not a scam."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "score": self.score,
            "reasons": self.reasons,
            "matched_prior_reports": self.matched_prior_reports,
            "highlights": self.highlights,
            "engine": self.engine,
            "model_assisted": self.model_assisted,
            "disclaimer": self.disclaimer,
        }


def _url_findings(urls: list[str]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for u in urls:
        host = u.split("/")[0].split(":")[0]
        if host in SHORTENERS:
            out.append((f"Link {host} is a link shortener that hides the real destination.", 0.35))
            continue
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            out.append(("A link points to a raw IP address instead of a name.", 0.40))
            continue
        if host.startswith("xn--") or ".xn--" in host:
            out.append((f"Link {host} uses look-alike international characters.", 0.40))
            continue
        brand_hit = None
        for brand, domains in OFFICIAL_DOMAINS.items():
            if brand in host.replace("-", "") and not any(host == d or host.endswith("." + d) for d in domains):
                brand_hit = brand
                break
        if brand_hit:
            out.append((f"Link {host} contains the name '{brand_hit}' but is not that organisation's official domain.", 0.50))
        elif host.endswith(RISKY_TLDS):
            out.append((f"Link {host} uses an ending often used for throw-away sites.", 0.30))
        elif host.count(".") >= 4:
            out.append((f"Link {host} has an unusually long chain of sub-domains.", 0.25))
    return out


def analyse_message(
    text: str,
    ctx: AnalysisContext | None = None,
    llm: LLMAdapter | None = None,
    llm_enabled: bool = False,
) -> AnalysisResult:
    ctx = ctx or AnalysisContext()
    reasons: list[dict[str, str]] = []
    highlights: list[dict[str, Any]] = []
    weights: list[float] = []
    kinds: set[str] = set()

    for key, (w, pat, why) in SIGNALS.items():
        ms = list(pat.finditer(text))
        if not ms:
            continue
        kinds.add(key)
        weights.append(w)
        reasons.append({"signal": key, "text": why, "evidence": ms[0].group(0)})
        highlights.extend({"start": m.start(), "end": m.end(), "signal": key} for m in ms)

    org = ORG_WORDS.search(text)
    urls = extract_urls(text)
    url_hits = _url_findings(urls)
    for why, w in url_hits:
        weights.append(w)
        kinds.add("url")
        reasons.append({"signal": "suspicious_url", "text": why, "evidence": ""})
    if org:
        weights.append(0.08)
        kinds.add("org")
        reasons.append({"signal": "organisation_named", "text": f"Names '{org.group(0)}'. Scammers often borrow trusted names.", "evidence": org.group(0)})
        highlights.append({"start": org.start(), "end": org.end(), "signal": "organisation_named"})
        if url_hits or "credential_request" in kinds:
            weights.append(0.20)
            reasons.append({"signal": "impersonation_pattern", "text": "A trusted name combined with a suspicious link or a request for credentials is a typical impersonation pattern.", "evidence": ""})

    matched: list[dict[str, Any]] = []
    priors: list[Prior] = []
    for u in urls:
        p = ctx.lookup_indicator("url", u)
        if p:
            priors.append(p)
    for ph in extract_phones(text):
        p = ctx.lookup_indicator("phone", ph)
        if p:
            priors.append(p)
    priors.extend(ctx.similar_messages(text))
    for p in priors:
        matched.append(
            {
                "indicator_id": p.indicator_id,
                "type": p.type,
                "value": p.value_masked,
                "status": p.status,
                "independent_reports": p.independent_reports,
                "match": p.match,
                "similarity": round(p.similarity, 2),
            }
        )
        boost = 0.35 if p.status == "verified" else 0.20
        if p.match == "similar":
            boost *= p.similarity
        weights.append(boost)
        kinds.add("prior")
        what = "matches" if p.match == "exact" else f"is {int(p.similarity * 100)}% similar to"
        reasons.append({"signal": "prior_report", "text": f"This {what} a {p.type} already reported by others ({p.independent_reports} independent report(s), status: {p.status}).", "evidence": ""})

    score = 1.0
    for w in weights:
        score *= 1 - w
    score = round(1 - score, 3)

    if score >= T_SEVERAL:
        label = "several_warning_signs"
    elif score >= T_SOME:
        label = "some_warning_signs"
    else:
        label = "few_warning_signs"

    n = len(kinds)
    length_factor = 0.0 if len(text.strip()) < 40 else 0.1 if len(text.strip()) < 120 else 0.15
    if label == "few_warning_signs":
        confidence = 0.35 + length_factor
        reasons.append({"signal": "none", "text": "No strong warning signs were found. That does not mean the message is safe.", "evidence": ""})
    else:
        confidence = min(0.95, 0.40 + 0.12 * n + length_factor + (0.10 if "prior" in kinds else 0.0))
    result = AnalysisResult(label=label, confidence=round(confidence, 2), score=score, reasons=reasons, matched_prior_reports=matched, highlights=sorted(highlights, key=lambda h: h["start"]))

    if llm is not None and llm_enabled:
        extra = llm.analyse(text)
        if extra:
            result.model_assisted = True
            result.engine += f"+{extra['model']}"
            for r in extra["reasons"]:
                result.reasons.append({"signal": "model_assisted", "text": r, "evidence": ""})
    return result
