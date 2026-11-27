from datetime import datetime, timedelta

import pytest

from scamshield.permissions import PERMISSIONS, can
from scamshield.rules import (
    ReportFact,
    VerifyPolicy,
    confidence_level,
    confidence_score,
    correction_due,
    correction_overdue,
    evaluate_verification,
    independent_count,
    is_independent_of_existing,
    public_status_label,
    risk_banner,
    suppress_small,
)

F = ReportFact


def test_distinct_accounts_and_buckets_are_independent():
    assert independent_count([F(1, 1, "a"), F(2, 2, "b"), F(3, 3, "c")]) == 3


def test_same_account_repeats_count_once():
    assert independent_count([F(1, 1, "a"), F(2, 1, "b"), F(3, 1, "c")]) == 1


def test_same_bucket_different_accounts_count_once():
    assert independent_count([F(1, 1, "a"), F(2, 2, "a")]) == 1


def test_transitive_grouping_account_then_bucket():
    # 1 and 2 share an account, 2 and 3 share a bucket: one group; 4 is independent
    assert independent_count([F(1, 1, "a"), F(2, 1, "b"), F(3, 9, "b"), F(4, 5, "z")]) == 2


def test_anonymous_reports_group_by_bucket_only_and_empty_bucket_never_groups():
    assert independent_count([F(1, None, "a"), F(2, None, "a"), F(3, None, "b")]) == 2
    assert independent_count([F(1, None, ""), F(2, None, "")]) == 2


def test_uncounted_reports_are_ignored_and_empty_is_zero():
    assert independent_count([F(1, 1, "a", counts=False)]) == 0
    assert independent_count([]) == 0


def test_is_independent_of_existing():
    ex = [F(1, 1, "a"), F(2, None, "b"), F(3, 7, "c", counts=False)]
    assert not is_independent_of_existing(ex, 1, "zzz")
    assert not is_independent_of_existing(ex, None, "b")
    assert is_independent_of_existing(ex, 7, "c")  # uncounted does not block
    assert is_independent_of_existing(ex, 2, "new")
    assert is_independent_of_existing(ex, None, "")


@pytest.mark.parametrize("n,primary,allow,ok,basis", [
    (3, False, True, True, "independent_reporters"), (5, True, True, True, "independent_reporters"),
    (1, True, True, True, "moderator_evidence"), (2, False, True, False, None), (0, False, False, False, None), (1, True, False, False, None),
])
def test_verification_policy(n, primary, allow, ok, basis):
    d = evaluate_verification(n, primary, VerifyPolicy(3, allow))
    assert (d.allowed, d.basis) == (ok, basis)
    if not ok:
        assert "needs" in d.reason


def test_verification_policy_is_configurable():
    assert evaluate_verification(2, False, VerifyPolicy(2, True)).allowed
    assert "or attach primary evidence" in evaluate_verification(0, False, VerifyPolicy(3, True)).reason
    assert "primary" not in evaluate_verification(0, False, VerifyPolicy(3, False)).reason


def test_confidence_monotonic_and_capped():
    base = confidence_score(0, 0, False, False, False)
    assert base == 0.10
    assert confidence_score(2, 0, False, False, False) > base
    assert confidence_score(2, 2, False, False, False) > confidence_score(2, 0, False, False, False)
    assert confidence_score(5, 3, True, True, False) == 1.0
    assert confidence_score(99, 99, True, True, False) == 1.0
    assert confidence_score(5, 3, True, True, True) == 0.40


def test_levels_and_labels_and_banner():
    assert confidence_level(0.8) == "high" and confidence_level(0.5) == "medium" and confidence_level(0.1) == "low"
    assert public_status_label("verified", False) == "Verified with evidence"
    assert public_status_label("unverified", False) == "Reported, not verified"
    assert public_status_label("verified", True) == "Disputed, under review"
    assert public_status_label("pending", False) == "No public record"
    assert risk_banner("pending", False, 0.9) == "none"
    assert risk_banner("verified", True, 0.9) == "med"
    assert risk_banner("verified", False, 0.9) == "high"
    assert risk_banner("unverified", False, 0.5) == "med"
    assert risk_banner("unverified", False, 0.2) == "none"


def test_correction_sla():
    t = datetime(2026, 1, 1)
    assert correction_due(t, 7, False) == t + timedelta(days=7)
    assert correction_due(t, 7, True) == t + timedelta(days=1)
    assert correction_overdue(t, t + timedelta(seconds=1), "open")
    assert not correction_overdue(t, t - timedelta(seconds=1), "open")
    assert not correction_overdue(t, t + timedelta(days=9), "accepted")


def test_small_count_suppression():
    assert suppress_small(4, 5) is None and suppress_small(5, 5) == 5


def test_permissions_table_least_privilege():
    assert can(None, "report.submit") and not can(None, "moderation.queue")
    assert not can("reporter", "moderation.queue") and can("moderator", "moderation.decide")
    assert not can("moderator", "admin.users") and can("platform_admin", "admin.users")
    assert not can("moderator", "corrections.remove") and can("platform_admin", "corrections.remove")
    assert can("org_admin", "dev.keys") and not can("org_analyst", "dev.keys")
    assert not can("org_admin", "evidence.view_all") and not can("platform_admin", "org.analytics")
    assert not can("nonsense", "report.submit")
    assert set(PERMISSIONS) == {"reporter", "contributor", "moderator", "org_analyst", "org_admin", "platform_admin"}
