from datetime import timedelta

import pyotp
import pytest
from sqlalchemy import select

from helpers import png_bytes, submit
from scamshield import accounts, notify, orgs
from scamshield.corrections import CorrectionError, CorrectionInvalid, decide_correction, queue, submit_correction
from scamshield.models import AlertSubscription, ApiUsage, AuditLog, Correction, Evidence, Indicator, MailOutbox, Notification, Report, Session, User, utcnow
from scamshield.moderation import decide
from scamshield.reports import exact_lookup
from scamshield.tenancy import TenantScope

GOOD = dict(relationship="owner", explanation="This number belongs to my shop and is not a scam number.", contact_email="owner@example.com", acknowledged=True)


def verified_indicator(db, settings, make, value="0700000001"):
    settings.verify_min_independent = 1
    mod, _ = make.user("moderator")
    r = submit(db, settings, value).report
    decide(db, settings, mod, r.id, "verify", "verified at lowered policy")
    db.commit()
    return db.get(Indicator, r.indicator_id), mod


# ---------------- corrections ----------------
def test_correction_flags_record_acknowledges_and_sets_sla(db, settings, make):
    ind, _ = verified_indicator(db, settings, make)
    c = submit_correction(db, settings, ind.id, **GOOD)
    db.commit()
    assert c.ref.startswith("C-") and c.due_at - c.acknowledged_at == timedelta(days=7)
    db.refresh(ind)
    assert ind.flagged and ind.confidence <= 0.40
    assert exact_lookup(db, "0700000001")[0].flagged
    mail = db.scalar(select(MailOutbox).where(MailOutbox.to_addr == "owner@example.com"))
    assert mail and "7 day" in mail.body
    assert db.scalar(select(AuditLog).where(AuditLog.action == "correction.submitted"))


@pytest.mark.parametrize("kw,field", [({"relationship": "x"}, "relationship"), ({"explanation": "short"}, "explanation"), ({"contact_email": "bad"}, "contact_email"), ({"acknowledged": False}, "acknowledged")])
def test_correction_validation(db, settings, make, kw, field):
    ind, _ = verified_indicator(db, settings, make)
    with pytest.raises(CorrectionInvalid) as e:
        submit_correction(db, settings, ind.id, **{**GOOD, **kw})
    assert field in e.value.errors


def test_correction_on_missing_or_pending_indicator_rejected(db, settings):
    with pytest.raises(CorrectionInvalid):
        submit_correction(db, settings, 999, **GOOD)
    r = submit(db, settings).report
    with pytest.raises(CorrectionInvalid):
        submit_correction(db, settings, r.indicator_id, **GOOD)


def test_urgent_legal_flagged_to_platform_admin_with_short_sla(db, settings, make):
    ind, _ = verified_indicator(db, settings, make)
    admin, _ = make.user("platform_admin")
    c = submit_correction(db, settings, ind.id, urgent_legal=True, **GOOD)
    db.commit()
    assert c.due_at - c.acknowledged_at == timedelta(days=1)
    assert db.scalar(select(Notification).where(Notification.user_id == admin.id, Notification.kind == "urgent_legal"))
    assert db.scalar(select(AuditLog).where(AuditLog.action == "correction.urgent_flagged"))


def test_accept_correction_softens_verified_record(db, settings, make):
    ind, mod = verified_indicator(db, settings, make)
    mod2, _ = make.user("moderator")
    c = submit_correction(db, settings, ind.id, **GOOD)
    with pytest.raises(CorrectionError, match="different moderator"):
        decide_correction(db, settings, mod, c.id, "accept", "I verified this myself")
    decide_correction(db, settings, mod2, c.id, "accept", "Owner proof is convincing.")
    db.commit()
    db.refresh(ind)
    assert ind.status == "unverified" and not ind.flagged and c.status == "accepted"
    with pytest.raises(CorrectionError, match="already decided"):
        decide_correction(db, settings, mod2, c.id, "decline", "second decision attempt")


def test_decline_keeps_status_clears_flag(db, settings, make):
    ind, _ = verified_indicator(db, settings, make)
    mod2, _ = make.user("moderator")
    c = submit_correction(db, settings, ind.id, **GOOD)
    decide_correction(db, settings, mod2, c.id, "decline", "Evidence unchanged after review.")
    db.refresh(ind)
    assert ind.status == "verified" and not ind.flagged


def test_flag_stays_while_another_correction_open(db, settings, make):
    ind, _ = verified_indicator(db, settings, make)
    mod2, _ = make.user("moderator")
    c1 = submit_correction(db, settings, ind.id, **GOOD)
    submit_correction(db, settings, ind.id, **GOOD)
    decide_correction(db, settings, mod2, c1.id, "decline", "first request declined")
    db.refresh(ind)
    assert ind.flagged


def test_removal_needs_platform_admin_and_scrubs_data(db, settings, make):
    ind, mod = verified_indicator(db, settings, make)
    r = db.scalar(select(Report))
    decide(db, settings, mod, r.id, "attach_evidence", "primary capture for removal test", file_bytes=png_bytes())
    ev = db.scalar(select(Evidence))
    from scamshield.uploads import path_for

    assert path_for(settings.storage_dir, ev.storage_name)
    mod2, _ = make.user("moderator")
    admin, _ = make.user("platform_admin")
    c = submit_correction(db, settings, ind.id, **GOOD)
    with pytest.raises(CorrectionError, match="platform administrator"):
        decide_correction(db, settings, mod2, c.id, "remove", "legal takedown requested")
    decide_correction(db, settings, admin, c.id, "remove", "Court order received (synthetic).")
    db.commit()
    db.refresh(ind)
    assert ind.status == "removed" and exact_lookup(db, "0700000001") == []
    assert db.scalar(select(Evidence)) is None and path_for(settings.storage_dir, ev.storage_name) is None
    db.refresh(r)
    assert r.raw_value == "[removed]" and r.description.startswith("[removed")


def test_correction_decision_validation(db, settings, make):
    ind, _ = verified_indicator(db, settings, make)
    mod2, _ = make.user("moderator")
    rep, _ = make.user("reporter")
    c = submit_correction(db, settings, ind.id, **GOOD)
    with pytest.raises(CorrectionError, match="permission"):
        decide_correction(db, settings, rep, c.id, "accept", "not allowed to decide")
    with pytest.raises(CorrectionError, match="reason"):
        decide_correction(db, settings, mod2, c.id, "accept", "no")
    with pytest.raises(CorrectionError, match="not found"):
        decide_correction(db, settings, mod2, 999, "accept", "no such correction")
    with pytest.raises(CorrectionError, match="Unknown"):
        decide_correction(db, settings, mod2, c.id, "shrug", "unknown decision value")


def test_queue_marks_overdue(db, settings, make):
    ind, _ = verified_indicator(db, settings, make)
    c = submit_correction(db, settings, ind.id, **GOOD)
    db.commit()
    assert queue(db)[0]["overdue"] is False
    assert queue(db, utcnow() + timedelta(days=8))[0]["overdue"] is True
    _ = c


# ---------------- accounts ----------------
def test_register_validation_and_duplicate(db):
    with pytest.raises(accounts.AccountError) as e:
        accounts.register(db, "bad", "short", "x", False)
    assert set(e.value.errors) == {"email", "password", "terms"}
    accounts.register(db, "Dup@Example.com", "Valid-Pass-12", "D", True)
    with pytest.raises(accounts.AccountError, match="already exists"):
        accounts.register(db, "dup@example.com", "Valid-Pass-12", "D", True)


def test_login_lockout_and_reset_on_success(db, settings, make):
    u, _ = make.user()
    for _i in range(settings.max_failed_logins):
        with pytest.raises(accounts.LoginFailed):
            accounts.authenticate(db, settings, u.email, "wrong-password-1")
    with pytest.raises(accounts.LockedOut):
        accounts.authenticate(db, settings, u.email, "Correct-Horse-9")
    u.locked_until = utcnow() - timedelta(minutes=1)
    assert accounts.authenticate(db, settings, u.email, "Correct-Horse-9").id == u.id
    assert u.failed_logins == 0


def test_login_unknown_user_and_bad_email_uniform_error(db, settings):
    for e in ("nobody@example.com", "not-an-email"):
        with pytest.raises(accounts.LoginFailed, match="Email or password"):
            accounts.authenticate(db, settings, e, "whatever-1")


def test_sessions_expire_and_end(db, settings, make):
    u, _ = make.user()
    tok = accounts.create_session(db, settings, u)
    db.commit()
    assert accounts.session_for(db, tok).user_id == u.id and accounts.session_for(db, None) is None and accounts.session_for(db, "junk") is None
    s = db.scalars(select(Session)).one()
    s.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert accounts.session_for(db, tok) is None
    s.expires_at = utcnow() + timedelta(hours=1)
    db.commit()
    accounts.end_session(db, tok)
    accounts.end_session(db, None)
    assert accounts.session_for(db, tok) is None


def test_mfa_enrolment_verification_recovery_and_lockout(db, settings, make):
    u, _ = make.user("moderator")
    u.totp_enabled, u.totp_secret_enc = False, None
    db.commit()
    tok = accounts.create_session(db, settings, u)
    sess = accounts.session_for(db, tok)
    assert not sess.mfa_passed and accounts.needs_mfa(settings, u)
    secret = accounts.begin_mfa_setup(settings, u)
    assert u.totp_secret_enc and secret not in u.totp_secret_enc
    with pytest.raises(accounts.AccountError):
        accounts.confirm_mfa_setup(db, settings, u, sess, "000000")
    codes = accounts.confirm_mfa_setup(db, settings, u, sess, pyotp.TOTP(secret).now())
    assert sess.mfa_passed and u.totp_enabled and len(codes) == 8
    # new session: wrong code, recovery code (single use), lockout after failures
    s2 = accounts.session_for(db, accounts.create_session(db, settings, u))
    with pytest.raises(accounts.LoginFailed):
        accounts.verify_mfa(db, settings, u, s2, "123456")
    accounts.verify_mfa(db, settings, u, s2, codes[0])
    assert s2.mfa_passed
    s3 = accounts.session_for(db, accounts.create_session(db, settings, u))
    with pytest.raises(accounts.LoginFailed):
        accounts.verify_mfa(db, settings, u, s3, codes[0])  # already used
    for _ in range(settings.max_failed_mfa - 1):
        with pytest.raises(accounts.LoginFailed):
            accounts.verify_mfa(db, settings, u, s3, "000000" if pyotp.TOTP(secret).now() != "000000" else "111111")
    with pytest.raises(accounts.LockedOut):
        accounts.verify_mfa(db, settings, u, s3, pyotp.TOTP(secret).now())


def test_non_mfa_role_session_is_immediately_complete(db, settings, make):
    u, _ = make.user("reporter")
    assert accounts.session_for(db, accounts.create_session(db, settings, u)).mfa_passed


def test_password_reset_flow(db, settings, make):
    u, _ = make.user()
    assert accounts.start_password_reset(db, "nobody@example.com") is None and accounts.start_password_reset(db, "bad") is None
    tok = accounts.start_password_reset(db, u.email)
    accounts.create_session(db, settings, u)
    with pytest.raises(accounts.AccountError, match="Password needs"):
        accounts.reset_password(db, tok, "weak")
    accounts.reset_password(db, tok, "Brand-New-Pass-5")
    assert accounts.authenticate(db, settings, u.email, "Brand-New-Pass-5")
    assert db.scalars(select(Session).where(Session.user_id == u.id)).all() == []
    with pytest.raises(accounts.AccountError, match="invalid or has expired"):
        accounts.reset_password(db, tok, "Another-Pass-77")
    with pytest.raises(accounts.AccountError):
        accounts.reset_password(db, "unknown-token", "Another-Pass-77")


def test_delete_account_anonymises_but_keeps_independence(db, settings, make):
    u, _ = make.user()
    r = submit(db, settings, reporter=u, consent_contact=True, contact_email="me@example.com").report
    accounts.create_session(db, settings, u)
    accounts.delete_account(db, u, "no longer needed")
    db.commit()
    assert u.deleted and u.email.startswith("deleted-") and r.contact_email is None and r.reporter_id == u.id
    with pytest.raises(accounts.LoginFailed):
        accounts.authenticate(db, settings, "deleted-1@invalid.example", "x")


# ---------------- notifications ----------------
def test_instant_alert_and_digest(db, settings, make):
    settings.verify_min_independent = 1
    mod, _ = make.user("moderator")
    inst, _ = make.user()
    daily, _ = make.user()
    off, _ = make.user()
    db.add_all([AlertSubscription(user_id=inst.id, category="reversal"), AlertSubscription(user_id=daily.id, category="reversal", frequency="daily"),
                AlertSubscription(user_id=off.id, category="reversal", enabled=False)])
    db.commit()
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "verify", "verified for alert test")
    db.commit()
    assert db.scalar(select(Notification).where(Notification.user_id == inst.id, Notification.kind == "new_verified"))
    assert db.scalar(select(Notification).where(Notification.user_id == off.id)) is None
    assert db.scalar(select(Notification).where(Notification.user_id == daily.id)) is None
    assert notify.run_digest(db) == 1
    assert notify.run_digest(db) == 0  # idempotent within the window
    assert db.scalar(select(Notification).where(Notification.user_id == daily.id, Notification.kind == "digest"))
    assert notify.run_digest(db, utcnow() + timedelta(days=2)) == 0  # nothing new


def test_alert_skips_restricted_and_deleted(db, settings, make):
    settings.verify_min_independent = 1
    mod, _ = make.user("moderator")
    a, _ = make.user()
    a.restricted = True
    db.add(AlertSubscription(user_id=a.id, category="reversal"))
    db.commit()
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "verify", "verified for alert skip test")
    assert db.scalar(select(Notification).where(Notification.user_id == a.id)) is None


def test_weekly_digest_waits_a_week(db, settings, make):
    u, _ = make.user()
    db.add(AlertSubscription(user_id=u.id, category="reversal", frequency="weekly", last_digest_at=utcnow() - timedelta(days=2)))
    db.commit()
    assert notify.run_digest(db) == 0


# ---------------- orgs ----------------
def test_api_key_lifecycle(db, settings, make):
    org = make.org()
    admin, _ = make.user("org_admin", org)
    scope = TenantScope(db, org.id)
    key, full = orgs.create_key(scope, admin, "Integration", ["lookup", "report"], "test", settings)
    db.commit()
    assert key.key_hash != full and full.startswith(key.prefix) and orgs.authenticate_key(db, full).id == key.id
    for bad, status in ((None, 401), ("ssk_nope", 401), (full + "x", 401)):
        with pytest.raises(orgs.ApiAuthError) as e:
            orgs.authenticate_key(db, bad)
        assert e.value.status == status
    scope.revoke_key(key.id)
    with pytest.raises(orgs.ApiAuthError, match="revoked"):
        orgs.authenticate_key(db, full)
    for kw in ({"name": ""}, {"name": "x" * 81}, {"scopes": []}, {"scopes": ["bogus"]}, {"environment": "live"}):
        args = {"name": "ok", "scopes": ["lookup"], "environment": "test", **kw}
        with pytest.raises(ValueError):
            orgs.create_key(scope, admin, args["name"], args["scopes"], args["environment"], settings)


def test_key_rate_limit_and_usage_summary(db, settings, make):
    org = make.org()
    admin, _ = make.user("org_admin", org)
    scope = TenantScope(db, org.id)
    key, _ = orgs.create_key(scope, admin, "k", ["lookup"], "test", settings)
    key.rate_per_minute = 2
    db.commit()
    assert orgs.check_rate(db, key).allowed and orgs.check_rate(db, key).allowed
    r = orgs.check_rate(db, key)
    assert not r.allowed and r.retry_after > 0
    orgs.log_usage(db, key, "GET /x", 200)
    orgs.log_usage(db, key, "GET /x", 429)
    orgs.log_usage(db, key, "GET /y", 404)
    u = orgs.usage_summary(scope)
    assert u["total"] == 3 and u["errors"] == 2 and u["throttled"] == 1 and u["by_endpoint"][0] == ("GET /x", 2)
    other = TenantScope(db, make.org().id)
    assert orgs.usage_summary(other)["total"] == 0
    _ = ApiUsage


def test_analytics_scope_suppression_and_csv_safety(db, settings, make):
    org, other = make.org(), make.org()
    for i in range(6):
        submit(db, settings, f"07000001{i:02d}", org=org, county="Nairobi", bucket=f"o{i}", category="phishing" if i % 2 else "reversal")
    submit(db, settings, "0700000199", org=org, county="Kisumu", bucket="ok")
    submit(db, settings, "0700000200", org=other, county="Nairobi", bucket="x")
    scope = TenantScope(db, org.id)
    a = orgs.analytics(scope, 7)
    assert a["total"] == 7 and dict(a["geo"])["Nairobi"] == 6 and dict(a["geo"])["Kisumu"] is None
    assert len(a["series"]) == 7 and orgs.analytics(TenantScope(db, other.id), 7)["total"] == 1
    assert orgs.network_trends(db)["verified_by_category"] == []
    rep = db.scalars(scope.reports()).first()
    rep.county = "=HYPERLINK(\"http://evil\")"
    rep.origin = "synthetic test data"
    db.commit()
    csv_text = orgs.export_csv(scope)
    assert csv_text.startswith("# Synthetic demonstration data") and "'=HYPERLINK" in csv_text
    assert "reporter" not in csv_text.splitlines()[1]
    assert csv_text.count("\n") == 9  # comment + header + 7 rows


def test_threat_intel(db, settings, make):
    ind, _ = verified_indicator(db, settings, make)
    items = orgs.threat_intel(db)
    assert items[0]["value"] == "+254700000001" and "reporter" not in repr(items)
    assert orgs.threat_intel(db, category="phishing") == []
    ind2, _ = verified_indicator(db, settings, make, "0700000002")
    assert len(orgs.threat_intel(db, "reversal")) == 2
    _ = (Correction, ind2)
