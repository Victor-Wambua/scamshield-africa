"""Critical business rules: independent-report counting, verification policy, confidence, SLA.

Pure functions over plain data so they can be tested exhaustively (see docs/COVERAGE.md).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ReportFact:
    id: int
    reporter_id: int | None
    device_bucket: str
    counts: bool = True  # False for rejected / withdrawn / merged-away reports


def independent_count(reports: Iterable[ReportFact]) -> int:
    """Number of independent reporters (Decision 1).

    Reports are grouped transitively when they share an account OR a device/IP-hash bucket;
    each group counts once. Repeats by one account, or several accounts behind one bucket,
    therefore never inflate the count. Anonymous reports are grouped by bucket alone; an empty
    bucket never groups with anything.
    """
    items = [r for r in reports if r.counts]
    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_account: dict[int, int] = {}
    by_bucket: dict[str, int] = {}
    for i, r in enumerate(items):
        if r.reporter_id is not None:
            if r.reporter_id in by_account:
                union(i, by_account[r.reporter_id])
            else:
                by_account[r.reporter_id] = i
        if r.device_bucket:
            if r.device_bucket in by_bucket:
                union(i, by_bucket[r.device_bucket])
            else:
                by_bucket[r.device_bucket] = i
    return len({find(i) for i in range(len(items))})


def is_independent_of_existing(
    existing: Iterable[ReportFact], reporter_id: int | None, device_bucket: str
) -> bool:
    """Would a new report from this reporter/bucket add to the independent count?"""
    for r in existing:
        if not r.counts:
            continue
        if reporter_id is not None and r.reporter_id == reporter_id:
            return False
        if device_bucket and r.device_bucket == device_bucket:
            return False
    return True


@dataclass(frozen=True)
class VerifyPolicy:
    min_independent: int = 3
    allow_moderator_evidence: bool = True


@dataclass(frozen=True)
class VerifyDecision:
    allowed: bool
    basis: str | None
    reason: str


def evaluate_verification(independent: int, has_moderator_primary_evidence: bool, policy: VerifyPolicy) -> VerifyDecision:
    """Decision 1: Verified with evidence needs a moderator AND (>=N independent reporters OR primary evidence)."""
    if independent >= policy.min_independent:
        return VerifyDecision(True, "independent_reporters", f"{independent} independent reporters")
    if has_moderator_primary_evidence and policy.allow_moderator_evidence:
        return VerifyDecision(True, "moderator_evidence", "moderator-attached primary evidence")
    need = policy.min_independent - independent
    extra = " or attach primary evidence" if policy.allow_moderator_evidence else ""
    return VerifyDecision(False, None, f"needs {need} more independent reporter(s){extra}")


def confidence_score(
    independent: int, evidence_count: int, has_primary: bool, verified: bool, flagged: bool
) -> float:
    """Evidence confidence 0..1 (documented in docs/DECISIONS.md; explained on the record page)."""
    score = 0.10 + 0.12 * min(independent, 5) + 0.08 * min(evidence_count, 3)
    if has_primary:
        score += 0.20
    if verified:
        score += 0.12
    if flagged:
        score = min(score, 0.40)
    return round(min(score, 1.0), 2)


def confidence_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def public_status_label(status: str, flagged: bool) -> str:
    if flagged and status in ("verified", "unverified"):
        return "Disputed, under review"
    return {"verified": "Verified with evidence", "unverified": "Reported, not verified"}.get(status, "No public record")


def risk_banner(status: str, flagged: bool, confidence: float) -> str:
    """Verdict banner class used by the record page (design: verdict high/med/none)."""
    if status not in ("verified", "unverified"):
        return "none"
    if flagged:
        return "med"
    if status == "verified":
        return "high"
    return "med" if confidence >= 0.45 else "none"


def correction_due(acknowledged: datetime, sla_days: int, urgent_legal: bool) -> datetime:
    """Decision 4: acknowledge immediately; decision target 7 days; urgent legal flagged for next-day."""
    return acknowledged + timedelta(days=1 if urgent_legal else sla_days)


def correction_overdue(due: datetime, now: datetime, status: str) -> bool:
    return status == "open" and now > due


def suppress_small(count: int, threshold: int) -> int | None:
    """Privacy: counts under the threshold are suppressed in geographic analytics."""
    return count if count >= threshold else None
