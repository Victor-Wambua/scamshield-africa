from datetime import datetime

import pytest
from helpers import DESC, png_bytes, submit
from sqlalchemy import select

from scamshield import audit
from scamshield.models import AuditLog, Evidence, Indicator, Notification, Report, ReviewEvent, User
from scamshield.moderation import ModerationError, decide
from scamshield.reports import (
    ReportInvalid,
    SubmitInput,
    browse,
    candidate_types,
    exact_lookup,
    history,
    message_priors,
    public_view,
    validate_input,
)


def test_submit_creates_pending_indicator_and_audit(db, settings):
    res = submit(db, settings)
    assert res.report.ref.startswith("R-") and res.indicator.status == "pending" and res.indicator.norm_value == "+254700000001"
    assert not res.is_duplicate and res.independent
    assert db.scalar(select(AuditLog).where(AuditLog.action == "report.submitted"))


def test_duplicate_detection_normalised_across_formats(db, settings):
    r1 = submit(db, settings, "0700 000 001", bucket="x1")
    r2 = submit(db, settings, "+254-700-000-001", bucket="x2")
    r3 = submit(db, settings, "254700000001", bucket="x3")
    assert r1.indicator.id == r2.indicator.id == r3.indicator.id
    assert r2.is_duplicate and r2.independent and r3.report.duplicate_of_id == r1.report.id
    assert db.scalar(select(Indicator).where(Indicator.type == "phone")).submission_count == 3


def test_urls_emails_wallets_dedupe(db, settings):
    a = submit(db, settings, "https://WWW.Evil.test/pay?utm_source=a", "url", bucket="u1")
    b = submit(db, settings, "evil.test/pay", "url", bucket="u2")
    assert a.indicator.id == b.indicator.id
    e1 = submit(db, settings, "A@Example.com", "email", bucket="e1")
    e2 = submit(db, settings, "a@example.com", "email", bucket="e2")
    assert e1.indicator.id == e2.indicator.id


def test_same_reporter_repeat_is_not_independent(db, settings, make):
    u, _ = make.user()
    submit(db, settings, reporter=u, bucket="b1")
    again = submit(db, settings, reporter=u, bucket="b2")
    assert again.is_duplicate and not again.independent and again.report.counts_independent is False


def test_same_device_other_account_not_independent(db, settings, make):
    u1, _ = make.user()
    u2, _ = make.user()
    submit(db, settings, reporter=u1, bucket="shared")
    assert not submit(db, settings, reporter=u2, bucket="shared").independent


@pytest.mark.parametrize("kw,field", [
    ({"itype": "bogus"}, "type"), ({"value": "123"}, "value"), ({"description": "too short"}, "description"), ({"category": "zzz"}, "category"),
    ({"amount_kes": -5}, "amount_kes"), ({"consent_privacy": False}, "consent_privacy"), ({"consent_truth": False}, "consent_truth"),
    ({"consent_contact": True, "contact_email": "nope"}, "contact_email"), ({"incident_date": datetime(2999, 1, 1)}, "incident_date"),
    ({"message_text": "x" * 5001}, "message_text"), ({"files": [b"x"] * 6}, "evidence"),
])
def test_validation_errors(settings, kw, field):
    base = dict(itype="phone", value="0700000001", description=DESC, category="reversal", consent_privacy=True, consent_truth=True)
    base.update(kw)
    _, errors = validate_input(SubmitInput(**base), settings)
    assert field in errors


def test_message_report_needs_text_and_runs_analysis(db, settings):
    with pytest.raises(ReportInvalid) as e:
        submit(db, settings, "", "message")
    assert "value" in e.value.errors
    res = submit(db, settings, "", "message", message_text="You have won KES 5000! Pay a processing fee to till 123456 urgently", category="prize")
    assert res.analysis and res.analysis["label"] != "few_warning_signs" and res.report.shingles_sig


def test_restricted_reporter_cannot_submit(db, settings, make):
    u, _ = make.user()
    u.restricted = True
    db.commit()
    with pytest.raises(ReportInvalid):
        submit(db, settings, reporter=u)


def test_evidence_upload_validated_and_bad_file_rejected(db, settings):
    res = submit(db, settings, files=[png_bytes()])
    assert db.scalar(select(Evidence).where(Evidence.report_id == res.report.id)).mime == "image/png"
    assert res.indicator.evidence_count == 1
    with pytest.raises(ReportInvalid) as e:
        submit(db, settings, "0700000002", files=[b"<script>alert(1)</script>"])
    assert "evidence" in e.value.errors


def test_contact_email_acknowledgement_logged_in_sandbox_mailer(db, settings, make):
    u, _ = make.user()
    submit(db, settings, reporter=u, consent_contact=True, contact_email="rep@example.com")
    from scamshield.models import MailOutbox

    m = db.scalar(select(MailOutbox).where(MailOutbox.to_addr == "rep@example.com"))
    assert m and m.origin == "mock integration"


# ---------------- public views ----------------
def test_pending_indicator_not_publicly_visible(db, settings):
    submit(db, settings)
    assert exact_lookup(db, "0700000001") == [] and browse(db) == []


def _accepted(db, settings, mod, value="0700000001", n=1):
    reps = []
    for i in range(n):
        reps.append(submit(db, settings, value, bucket=f"bk-{value}-{i}").report)
    for r in reps:
        decide(db, settings, mod, r.id, "accept", "Looks consistent with other reports.")
    db.commit()
    return reps


def test_public_view_never_leaks_reporter_or_evidence(db, settings, make):
    mod, _ = make.user("moderator")
    u, _ = make.user()
    submit(db, settings, reporter=u, bucket="p1", files=[png_bytes()], description="My name is Secret Person and I live at Hidden Estate, call me.")
    r = db.scalar(select(Report))
    decide(db, settings, mod, r.id, "accept", "Accepted after review.")
    db.commit()
    ind = db.get(Indicator, r.indicator_id)
    pub = public_view(ind, exact=False)
    blob = repr(pub)
    for forbidden in ("Secret Person", "Hidden Estate", str(u.email), "storage", "sha256", "reporter_id", "device_bucket", "description"):
        assert forbidden not in blob
    assert pub["masked"] and pub["value"] == "+2547•• ••• 001"
    assert public_view(ind, exact=True)["value"] == "+254700000001"
    staff = public_view(ind, exact=False, staff=True)
    assert staff["value"] == "+254700000001" and staff["submissions"] == 1


def test_exact_lookup_tries_types_and_browse_filters(db, settings, make):
    mod, _ = make.user("moderator")
    _accepted(db, settings, mod, "0700000001")
    assert exact_lookup(db, "0700 000 001")[0].type == "phone"
    assert exact_lookup(db, "0700000001", "phone") and not exact_lookup(db, "0700000001", "email")
    assert browse(db, itype="phone") and not browse(db, itype="url") and browse(db, status="unverified", category="reversal")
    assert candidate_types("!!", None) == [] and candidate_types("0700000001", "url") == []


def test_history_hides_staff_fields_from_public(db, settings, make):
    mod, _ = make.user("moderator")
    _accepted(db, settings, mod)
    ind = db.scalar(select(Indicator))
    assert "actor_id" not in history(db, ind, False)[0] and "reason" not in history(db, ind, False)[0]
    assert "actor_id" in history(db, ind, True)[0] and history(db, ind, True)[0]["reason"]


# ---------------- moderation ----------------
def test_verify_blocked_until_policy_met_then_allowed_with_three_independent(db, settings, make):
    mod, _ = make.user("moderator")
    r = [submit(db, settings, bucket=f"v{i}").report for i in range(3)]
    decide(db, settings, mod, r[0].id, "accept", "reviewed report one")
    with pytest.raises(ModerationError, match="needs 1 more"):
        decide(db, settings, mod, r[1].id, "verify", "trying to verify early")
    decide(db, settings, mod, r[1].id, "accept", "reviewed report two")
    ind = db.get(Indicator, r[0].indicator_id)
    decide(db, settings, mod, r[2].id, "verify", "three independent reporters agree")
    db.commit()
    db.refresh(ind)
    assert ind.status == "verified" and ind.verified_basis == "independent_reporters" and ind.independent_count == 3 and ind.verified_by == mod.id


def test_same_reporter_three_times_cannot_verify(db, settings, make):
    mod, _ = make.user("moderator")
    u, _ = make.user()
    rs = [submit(db, settings, reporter=u, bucket=f"s{i}").report for i in range(3)]
    for r in rs[:2]:
        decide(db, settings, mod, r.id, "accept", "accepting for the record")
    with pytest.raises(ModerationError):
        decide(db, settings, mod, rs[2].id, "verify", "should not be allowed")
    assert db.get(Indicator, rs[0].indicator_id).independent_count == 1


def test_verify_via_moderator_primary_evidence(db, settings, make):
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    with pytest.raises(ModerationError):
        decide(db, settings, mod, r.id, "verify", "no evidence yet so refuse")
    decide(db, settings, mod, r.id, "attach_evidence", "captured the live page myself", file_bytes=png_bytes())
    decide(db, settings, mod, r.id, "verify", "primary evidence attached by moderator")
    ind = db.get(Indicator, r.indicator_id)
    assert ind.status == "verified" and ind.verified_basis == "moderator_evidence" and ind.confidence >= 0.5


def test_policy_configurable_min_independent(db, settings, make):
    settings.verify_min_independent = 1
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "verify", "policy lowered for this deployment")
    assert db.get(Indicator, r.indicator_id).status == "verified"


def test_mod_actions_require_reason_permission_and_no_self_review(db, settings, make):
    mod, _ = make.user("moderator")
    rep_user, _ = make.user("reporter")
    r = submit(db, settings).report
    with pytest.raises(ModerationError, match="reason"):
        decide(db, settings, mod, r.id, "accept", "short")
    with pytest.raises(ModerationError, match="permission"):
        decide(db, settings, rep_user, r.id, "accept", "reporters cannot moderate")
    with pytest.raises(ModerationError, match="Unknown"):
        decide(db, settings, mod, r.id, "explode", "not a real action")
    with pytest.raises(ModerationError, match="not found"):
        decide(db, settings, mod, 9999, "accept", "no such report here")
    own = submit(db, settings, "0700000009", reporter=mod, bucket="mine").report
    with pytest.raises(ModerationError, match="own report"):
        decide(db, settings, mod, own.id, "accept", "reviewing my own report")


def test_accept_reject_request_evidence_flow_and_notifications(db, settings, make):
    mod, _ = make.user("moderator")
    u, _ = make.user()
    r = submit(db, settings, reporter=u).report
    decide(db, settings, mod, r.id, "request_evidence", "Please add a screenshot of the call log.")
    assert r.status == "awaiting_evidence" and "screenshot" in r.evidence_request
    assert db.scalar(select(Notification).where(Notification.user_id == u.id, Notification.kind == "status_change"))
    decide(db, settings, mod, r.id, "reject", "Cannot corroborate this report.")
    assert r.status == "rejected"
    with pytest.raises(ModerationError, match="closed"):
        decide(db, settings, mod, r.id, "accept", "reopening a closed report")
    with pytest.raises(ModerationError, match="closed"):
        decide(db, settings, mod, r.id, "request_evidence", "asking after closing it")
    with pytest.raises(ModerationError, match="closed"):
        decide(db, settings, mod, r.id, "verify", "verify after reject must fail")
    with pytest.raises(ModerationError, match="closed"):
        decide(db, settings, mod, r.id, "reject", "reject twice must fail too")
    assert db.get(Indicator, r.indicator_id).independent_count == 0


def test_notification_respects_user_preference(db, settings, make):
    from scamshield.models import NotificationPref

    mod, _ = make.user("moderator")
    u, _ = make.user()
    db.get(NotificationPref, u.id).on_status_change = False
    db.commit()
    r = submit(db, settings, reporter=u).report
    decide(db, settings, mod, r.id, "accept", "accepted after review")
    assert db.scalar(select(Notification).where(Notification.user_id == u.id)) is None


def test_mark_unverified_downgrades_verified(db, settings, make):
    settings.verify_min_independent = 1
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "verify", "verify at lowered policy")
    ind = db.get(Indicator, r.indicator_id)
    decide(db, settings, mod, r.id, "mark_unverified", "new doubt about this record")
    db.refresh(ind)
    assert ind.status == "unverified" and ind.verified_basis is None


def test_merge_moves_report_and_keeps_independence_rules(db, settings, make):
    mod, _ = make.user("moderator")
    u, _ = make.user()
    a = submit(db, settings, "evil-one.test", "url", reporter=u, bucket="m1").report
    b = submit(db, settings, "evil-two.test", "url", reporter=u, bucket="m2").report
    decide(db, settings, mod, a.id, "accept", "accept the first variant")
    ind_a, ind_b = db.get(Indicator, a.indicator_id), db.get(Indicator, b.indicator_id)
    decide(db, settings, mod, b.id, "merge", "same campaign as the first domain", target_indicator_id=ind_a.id)
    db.commit()
    db.refresh(ind_a)
    db.refresh(ind_b)
    assert b.status == "merged" and b.indicator_id == ind_a.id and b.duplicate_of_id == a.id
    assert ind_a.independent_count == 1  # same reporter keeps count
    assert ind_b.status == "removed"
    for bad in (None, ind_a.id, 9999):
        c = submit(db, settings, f"x{bad}.test", "url", bucket=f"q{bad}").report
        with pytest.raises(ModerationError, match="different"):
            decide(db, settings, mod, c.id, "merge", "bad merge target choice", target_indicator_id=bad if bad != ind_a.id else db.get(Indicator, c.indicator_id).id)


def test_merge_into_pending_publishes_target_and_keeps_old_if_other_reports(db, settings, make):
    mod, _ = make.user("moderator")
    a = submit(db, settings, "alpha-scam.test", "url", bucket="n1").report
    b = submit(db, settings, "beta-scam.test", "url", bucket="n2").report
    b2 = submit(db, settings, "beta-scam.test", "url", bucket="n3").report
    decide(db, settings, mod, b.id, "merge", "merge b into a campaign", target_indicator_id=a.indicator_id)
    assert db.get(Indicator, a.indicator_id).status == "unverified"
    assert db.get(Indicator, b2.indicator_id).status == "pending"  # still has a live report


def test_restrict_reporter(db, settings, make):
    mod, _ = make.user("moderator")
    admin, _ = make.user("platform_admin")
    u, _ = make.user()
    r = submit(db, settings, reporter=u).report
    anon = submit(db, settings, "0700000044", bucket="z").report
    with pytest.raises(ModerationError, match="anonymous"):
        decide(db, settings, mod, anon.id, "restrict_reporter", "abusive submissions pattern")
    decide(db, settings, mod, r.id, "restrict_reporter", "abusive submissions pattern")
    assert db.get(User, u.id).restricted
    own = submit(db, settings, "0700000045", reporter=admin, bucket="a").report
    other = make.user("moderator")[0]
    with pytest.raises(ModerationError, match="Staff"):
        decide(db, settings, other, own.id, "restrict_reporter", "trying to restrict staff")


def test_attach_evidence_validation(db, settings, make):
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    with pytest.raises(ModerationError, match="Attach"):
        decide(db, settings, mod, r.id, "attach_evidence", "no file supplied here")
    with pytest.raises(ModerationError, match="images"):
        decide(db, settings, mod, r.id, "attach_evidence", "bad file supplied here", file_bytes=b"MZ-not-an-image")


def test_every_decision_is_audited_with_actor_and_history(db, settings, make):
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "accept", "reviewed and accepted")
    db.commit()
    a = db.scalar(select(AuditLog).where(AuditLog.action == "moderation.accept"))
    assert a.actor_id == mod.id and a.reason == "reviewed and accepted" and a.target_id == str(r.id)
    assert db.scalar(select(ReviewEvent).where(ReviewEvent.action == "accepted", ReviewEvent.actor_id == mod.id))
    assert audit.verify_chain(db)[0]


def test_message_similarity_priors(db, settings, make):
    mod, _ = make.user("moderator")
    m1 = submit(db, settings, "", "message", message_text="Congratulations you have won KES 250000 in the lottery pay a processing fee to till 123456 to claim today", category="prize", bucket="a").report
    decide(db, settings, mod, m1.id, "accept", "classic prize message")
    pri = message_priors(db, "CONGRATULATIONS you have won KES 999 in the lottery! Pay processing fee to till 222 to claim today")
    assert pri and pri[0].match == "similar" and pri[0].similarity > 0.5
    assert message_priors(db, "") == []
    assert message_priors(db, "totally different text about lunch and the weather today friends") == []
    assert message_priors(db, "Congratulations you have won KES 250000 in the lottery pay a processing fee to till 123456 to claim today", exclude_report_id=m1.id) == []
