"""Report intake, duplicate detection, indicator statistics and public lookup."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import audit, mailer
from .analysis import AnalysisContext, Prior, analyse_message
from .config import Settings
from .models import CATEGORIES, INDICATOR_TYPES, Evidence, Indicator, Report, ReviewEvent, User, utcnow
from .normalize import InvalidIndicator, detect_type, mask_value, normalize
from .rules import (
    ReportFact,
    VerifyPolicy,
    confidence_level,
    confidence_score,
    independent_count,
    is_independent_of_existing,
    public_status_label,
    risk_banner,
)
from .similarity import minhash, most_similar
from .uploads import UploadRejected, store_image

COUNTED = ("accepted", "merged")  # statuses that count towards public/verification numbers
LIVE = ("received", "in_review", "awaiting_evidence", "accepted", "merged")
PUBLIC_STATUSES = ("unverified", "verified")


class ReportInvalid(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


@dataclass
class SubmitInput:
    itype: str
    value: str
    description: str
    category: str = "other"
    message_text: str | None = None
    incident_date: datetime | None = None
    amount_kes: int | None = None
    county: str | None = None
    consent_privacy: bool = False
    consent_truth: bool = False
    consent_share_partners: bool = False
    consent_contact: bool = False
    contact_email: str | None = None
    files: list[bytes] = field(default_factory=list)


@dataclass
class SubmitResult:
    report: Report
    indicator: Indicator
    is_duplicate: bool
    independent: bool
    analysis: dict[str, Any] | None


def policy_of(settings: Settings) -> VerifyPolicy:
    return VerifyPolicy(settings.verify_min_independent, settings.verify_allow_moderator_evidence)


def validate_input(inp: SubmitInput, settings: Settings, now: datetime | None = None) -> tuple[str, dict[str, str]]:
    errors: dict[str, str] = {}
    norm = ""
    if inp.itype not in INDICATOR_TYPES:
        errors["type"] = "Choose what you are reporting."
    else:
        try:
            norm = normalize(inp.itype, inp.message_text if inp.itype == "message" and inp.message_text else inp.value)
        except InvalidIndicator as exc:
            errors["value"] = f"Check the value: {exc}."
    if inp.itype == "message" and not (inp.message_text and inp.message_text.strip()):
        errors["value"] = "Paste the message text."
    d = (inp.description or "").strip()
    if not 20 <= len(d) <= 2000:
        errors["description"] = "Describe what happened in 20 to 2,000 characters."
    if inp.category not in CATEGORIES:
        errors["category"] = "Choose a category."
    if inp.incident_date and inp.incident_date > (now or utcnow()):
        errors["incident_date"] = "The date cannot be in the future."
    if inp.amount_kes is not None and inp.amount_kes < 0:
        errors["amount_kes"] = "Enter an amount of 0 or more (whole shillings)."
    if inp.message_text and len(inp.message_text) > 5000:
        errors["message_text"] = "Message text is limited to 5,000 characters."
    if not inp.consent_privacy:
        errors["consent_privacy"] = "You must accept the privacy notice."
    if not inp.consent_truth:
        errors["consent_truth"] = "Please confirm your report is truthful to the best of your knowledge."
    if inp.consent_contact:
        try:
            normalize("email", inp.contact_email or "")
        except InvalidIndicator:
            errors["contact_email"] = "Enter a valid email address for follow-up."
    if len(inp.files) > settings.max_uploads_per_report:
        errors["evidence"] = f"At most {settings.max_uploads_per_report} images."
    return norm, errors


def next_ref(db: Session, prefix: str, model: Any) -> str:
    n = (db.scalar(select(func.max(model.id))) or 0) + 1
    return f"{prefix}-{n:04d}"


def message_priors(db: Session, text: str, exclude_report_id: int | None = None) -> list[Prior]:
    sig = minhash(text)
    if not sig:
        return []
    rows = db.execute(
        select(Report.id, Report.shingles_sig, Report.indicator_id)
        .where(Report.shingles_sig.is_not(None), Report.status.in_(COUNTED + ("received", "in_review")))
        .order_by(Report.id.desc())
        .limit(2000)
    ).all()
    cand = [(r.id, r.shingles_sig) for r in rows if r.id != exclude_report_id and r.shingles_sig]
    by_id = {r.id: r.indicator_id for r in rows}
    out: list[Prior] = []
    seen: set[int] = set()
    for rid, sim in most_similar(sig, cand, threshold=0.5):
        ind = db.get(Indicator, by_id[rid])
        if ind is None or ind.id in seen:
            continue
        seen.add(ind.id)
        out.append(Prior(ind.id, ind.type, mask_value(ind.type, ind.norm_value), ind.status, ind.independent_count, "similar", sim))
    return out


def analysis_context(db: Session) -> AnalysisContext:
    def lookup(t: str, v: str) -> Prior | None:
        ind = db.scalar(select(Indicator).where(Indicator.type == t, Indicator.norm_value == v, Indicator.status.in_(PUBLIC_STATUSES)))
        if ind is None:
            return None
        return Prior(ind.id, ind.type, mask_value(ind.type, ind.norm_value), ind.status, ind.independent_count, "exact")

    def similar(text: str) -> list[Prior]:
        return [p for p in message_priors(db, text) if p.status in PUBLIC_STATUSES]

    return AnalysisContext(lookup_indicator=lookup, similar_messages=similar)


def _observed(r: Report) -> datetime:
    d = r.incident_date or r.created_at
    return d if d <= utcnow() else r.created_at


def recompute_indicator(db: Session, ind: Indicator, settings: Settings) -> Indicator:
    reps = list(db.scalars(select(Report).where(Report.indicator_id == ind.id)))
    live = [r for r in reps if r.status in LIVE]
    counted = [r for r in reps if r.status in COUNTED]
    facts = [ReportFact(r.id, r.reporter_id, r.device_bucket, True) for r in counted]
    ind.independent_count = independent_count(facts)
    ind.submission_count = len(live)
    ev = list(db.scalars(select(Evidence).where(Evidence.indicator_id == ind.id)))
    ind.evidence_count = len(ev)
    has_primary = any(e.primary_by_moderator for e in ev)
    if live:
        ind.first_reported = min(r.created_at for r in live)
        ind.last_observed = max(_observed(r) for r in live)
        cats = Counter(r.category for r in live)
        ind.risk_category = cats.most_common(1)[0][0]
    ind.confidence = confidence_score(ind.independent_count, ind.evidence_count, has_primary, ind.status == "verified", ind.flagged)
    ind.updated_at = utcnow()
    db.flush()
    return ind


def get_or_create_indicator(db: Session, itype: str, norm: str, origin: str) -> tuple[Indicator, bool]:
    ind = db.scalar(select(Indicator).where(Indicator.type == itype, Indicator.norm_value == norm))
    if ind:
        return ind, False
    ind = Indicator(type=itype, norm_value=norm, status="pending", origin=origin)
    db.add(ind)
    db.flush()
    return ind, True


def submit_report(
    db: Session,
    settings: Settings,
    inp: SubmitInput,
    *,
    reporter: User | None,
    bucket: str,
    owning_org_id: int | None = None,
    api_key_id: int | None = None,
    origin: str = "user-submitted",
) -> SubmitResult:
    norm, errors = validate_input(inp, settings)
    if errors:
        raise ReportInvalid(errors)
    if reporter is not None and reporter.restricted:
        raise ReportInvalid({"account": "Your account is restricted from submitting reports. You can contact support."})
    stored = []
    try:
        for data in inp.files:
            stored.append(store_image(settings.storage_dir, data, settings.max_upload_bytes, settings.max_image_pixels))
    except UploadRejected as exc:
        raise ReportInvalid({"evidence": str(exc)}) from exc

    ind, created = get_or_create_indicator(db, inp.itype, norm, origin)
    existing = list(db.scalars(select(Report).where(Report.indicator_id == ind.id, Report.status.in_(LIVE))))
    facts = [ReportFact(r.id, r.reporter_id, r.device_bucket, True) for r in existing]
    independent = is_independent_of_existing(facts, reporter.id if reporter else None, bucket)
    text_for_sim = inp.message_text or (inp.description if inp.itype == "message" else None)
    sig = minhash(text_for_sim) if text_for_sim else None
    rep = Report(
        ref="R-PENDING",
        indicator_id=ind.id,
        reporter_id=reporter.id if reporter else None,
        device_bucket=bucket,
        owning_org_id=owning_org_id,
        api_key_id=api_key_id,
        itype=inp.itype,
        raw_value=inp.value.strip()[:600] if inp.itype != "message" else (inp.message_text or "")[:600],
        category=inp.category,
        description=inp.description.strip(),
        message_text=inp.message_text,
        incident_date=inp.incident_date,
        amount_kes=inp.amount_kes,
        county=inp.county,
        consent_privacy=True,
        consent_share_partners=inp.consent_share_partners,
        consent_contact=inp.consent_contact,
        contact_email=inp.contact_email if inp.consent_contact else None,
        status="received",
        duplicate_of_id=existing[0].id if existing else None,
        counts_independent=independent,
        shingles_sig=sig,
        origin=origin,
    )
    db.add(rep)
    db.flush()
    rep.ref = f"R-{rep.id:04d}"
    analysis = None
    if text_for_sim:
        ctx = analysis_context(db)
        analysis = analyse_message(text_for_sim, ctx).as_dict()
        rep.analysis = analysis
    for sf in stored:
        db.add(Evidence(report_id=rep.id, indicator_id=ind.id, storage_name=sf.storage_name, mime=sf.mime, size=sf.size, sha256=sf.sha256, origin=origin))
    db.flush()
    audit.record(db, reporter.id if reporter else None, "report.submitted", "report", rep.id, detail={"indicator_id": ind.id, "duplicate": bool(existing), "independent": independent, "org": owning_org_id})
    if reporter and rep.consent_contact and rep.contact_email:
        mailer.send(db, rep.contact_email, f"We received your report {rep.ref}", f"Thank you. Your report {rep.ref} will be reviewed by a moderator. This does not mean the indicator is confirmed.")
    recompute_indicator(db, ind, settings)
    return SubmitResult(rep, ind, bool(existing), independent, analysis)


# ---------------- public views ----------------
def candidate_types(q: str, hint: str | None) -> list[tuple[str, str]]:
    types = [hint] if hint in INDICATOR_TYPES else ["phone", "email", "url", "wallet", "social", "payment_ref"]
    seen: list[tuple[str, str]] = []
    for t in types:
        assert t is not None
        try:
            n = normalize(t, q)
        except InvalidIndicator:
            continue
        if (t, n) not in seen:
            seen.append((t, n))
    return seen


def exact_lookup(db: Session, q: str, hint: str | None = None) -> list[Indicator]:
    """Exact-match lookup on normalised value. Pending/removed indicators are never returned."""
    out: list[Indicator] = []
    for t, n in candidate_types(q, hint):
        ind = db.scalar(select(Indicator).where(Indicator.type == t, Indicator.norm_value == n, Indicator.status.in_(PUBLIC_STATUSES)))
        if ind:
            out.append(ind)
    return out


def public_view(ind: Indicator, *, exact: bool, staff: bool = False) -> dict[str, Any]:
    """Public projection. Never includes reporter identity, evidence or free text (Decisions 2 and 3)."""
    d: dict[str, Any] = {
        "id": ind.id,
        "type": ind.type,
        "value": ind.norm_value if exact or staff else mask_value(ind.type, ind.norm_value),
        "masked": not (exact or staff),
        "status": ind.status,
        "status_label": public_status_label(ind.status, ind.flagged),
        "disputed": ind.flagged,
        "risk_category": ind.risk_category,
        "independent_reports": ind.independent_count,
        "evidence_confidence": ind.confidence,
        "confidence_level": confidence_level(ind.confidence),
        "banner": risk_banner(ind.status, ind.flagged, ind.confidence),
        "first_reported": ind.first_reported.date().isoformat(),
        "last_observed": ind.last_observed.date().isoformat(),
        "last_updated": ind.updated_at.date().isoformat(),
        "source": ind.source,
        "origin": ind.origin,
    }
    if ind.type == "message":
        d["value"] = "Message pattern (text not shown publicly)"
    if staff:
        d["submissions"] = ind.submission_count
        d["evidence_items"] = ind.evidence_count
    return d


def browse(db: Session, *, itype: str | None = None, status: str | None = None, category: str | None = None, limit: int = 30) -> list[Indicator]:
    stmt = select(Indicator).where(Indicator.status.in_(PUBLIC_STATUSES))
    if itype in INDICATOR_TYPES:
        stmt = stmt.where(Indicator.type == itype)
    if status in PUBLIC_STATUSES:
        stmt = stmt.where(Indicator.status == status)
    if category in CATEGORIES:
        stmt = stmt.where(Indicator.risk_category == category)
    stmt = stmt.order_by(Indicator.last_observed.desc(), Indicator.id.desc()).limit(limit)
    return list(db.scalars(stmt))


def history(db: Session, ind: Indicator, staff: bool) -> list[dict[str, Any]]:
    rows = db.scalars(select(ReviewEvent).where(ReviewEvent.indicator_id == ind.id).order_by(ReviewEvent.id))
    out = []
    for e in rows:
        label = {
            "accepted": "Report accepted as unverified", "verified": "Verified with evidence", "unverified": "Marked not verified",
            "merged": "Duplicate report merged", "correction_requested": "Correction requested", "correction_accepted": "Correction accepted: record softened",
            "correction_declined": "Correction request declined after review", "evidence_attached": "Moderator attached primary evidence",
        }.get(e.action, e.action.replace("_", " ").capitalize())
        item: dict[str, Any] = {"date": e.created_at.date().isoformat(), "event": label}
        if staff:
            item["actor_id"] = e.actor_id
            item["reason"] = e.reason
        out.append(item)
    return out


SAFETY_ADVICE = {
    "reversal": "Do not send money back on a message alone. Check your own M-Pesa statement and call the provider using a number from their official site.",
    "phishing": "Do not click the link or enter any PIN, password or code. Go to the organisation's official website or app by typing the address yourself.",
    "investment": "Be wary of guaranteed returns. Check the company on regulator registers before sending money.",
    "jobs": "Real employers do not ask you to pay to get a job. Do not share ID documents until you have verified the employer.",
    "tax": "KRA and other agencies do not ask for PINs or payments by message. Use the official portal.",
    "impersonation": "Call the real person or organisation on a number you already trust before acting.",
    "prize": "You cannot win a prize you did not enter. Never pay to collect one.",
    "other": "Pause before paying or replying. Verify through an official channel you find yourself.",
}
GENERAL_ADVICE = [
    "Never share your M-Pesa PIN, bank PIN, password or one-time codes with anyone.",
    "Pause when a message creates pressure to act quickly.",
    "If you already sent money, contact your provider immediately and report to the police.",
]
