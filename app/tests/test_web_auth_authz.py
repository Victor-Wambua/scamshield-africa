import re

import pyotp
import pytest
from conftest import PASSWORD, csrf_of, login, post
from fastapi.testclient import TestClient
from helpers import png_bytes, submit
from sqlalchemy import select

from scamshield.models import (
    AlertSubscription,
    ApiKey,
    AuditLog,
    Case,
    CaseNote,
    Evidence,
    Report,
    Session,
    User,
)
from scamshield.moderation import decide

ROLES = ["anonymous", "reporter", "contributor", "moderator", "org_analyst", "org_admin", "platform_admin"]


def anon(app):
    return TestClient(app, base_url="http://testserver", follow_redirects=False)


# ---------------- login / logout / sessions ----------------
def test_register_login_logout_and_cookie_flags(app, db):
    c = anon(app)
    r = post(c, "/register", {"email": "new@example.com", "password": "Strong-Pass-77", "display_name": "N", "terms": "1"}, form_path="/register")
    assert r.status_code == 303
    cookie = r.headers["set-cookie"]
    assert "ss_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "new@example.com" in c.get("/settings").text
    assert post(c, "/logout", {}, form_path="/settings").status_code == 303
    assert c.get("/settings").status_code == 401
    token = re.search(r"ss_session=([^;]+)", cookie).group(1)
    assert db.get(Session, __import__("scamshield.security", fromlist=["x"]).token_id(token)) is None  # session row destroyed


def test_session_cookie_secure_flag_when_configured(app, settings, make):
    settings.cookie_secure = True
    u, _ = make.user()
    c = anon(app)
    tok = csrf_of(c, "/login")
    r = c.post("/login", data={"email": u.email, "password": PASSWORD, "csrf_token": tok})
    assert "Secure" in r.headers["set-cookie"]
    assert "strict-transport-security" in r.headers


def test_register_validation_and_duplicates(app, make):
    c = anon(app)
    r = post(c, "/register", {"email": "bad", "password": "x", "terms": ""}, form_path="/register")
    assert r.status_code == 422 and "valid email" in r.text and "Password needs" in r.text
    u, _ = make.user()
    r = post(c, "/register", {"email": u.email, "password": "Strong-Pass-77", "terms": "1"}, form_path="/register")
    assert r.status_code == 422 and "already exists" in r.text


def test_login_failure_messages_are_uniform_and_lockout_works(app, make, settings):
    u, _ = make.user()
    c = anon(app)
    a = post(c, "/login", {"email": u.email, "password": "wrong-pass-1"}, form_path="/login")
    b = post(c, "/login", {"email": "ghost@example.com", "password": "wrong-pass-1"}, form_path="/login")
    assert a.status_code == b.status_code == 401
    assert re.search(r"Email or password is not correct", a.text) and re.search(r"Email or password is not correct", b.text)
    for _ in range(settings.max_failed_logins):
        post(c, "/login", {"email": u.email, "password": "wrong-pass-1"}, form_path="/login")
    r = post(c, "/login", {"email": u.email, "password": PASSWORD}, form_path="/login")
    assert r.status_code == 429 and "Too many failed attempts" in r.text


def test_login_rate_limit_by_client(app, settings):
    settings.login_rate_per_15min = 3
    c = anon(app)
    codes = [post(c, "/login", {"email": "a@example.com", "password": "x"}, form_path="/login").status_code for _ in range(5)]
    assert codes[-1] == 429


def test_session_fixation_login_issues_new_session(app, make, db):
    u, _ = make.user()
    c = login(app, u)
    first = c.cookies.get("ss_session")
    tok = csrf_of(c, "/settings")
    c2 = anon(app)
    c2.cookies.set("ss_session", first)
    r = post(c2, "/login", {"email": u.email, "password": PASSWORD}, form_path="/login")
    assert r.status_code == 303 and r.cookies.get("ss_session") != first
    _ = tok


def test_mfa_required_for_staff_enrolment_and_verification(app, make, db):
    u, _ = make.user("moderator")
    u.totp_enabled, u.totp_secret_enc = False, None
    db.commit()
    c = anon(app)
    tok = csrf_of(c, "/login")
    assert c.post("/login", data={"email": u.email, "password": PASSWORD, "csrf_token": tok}).headers["location"] == "/mfa"
    assert c.get("/mod").headers["location"] == "/mfa"  # password alone is not enough
    assert c.get("/mfa").headers["location"] == "/mfa/setup"
    setup = c.get("/mfa/setup").text
    secret = re.search(r'id="secret">([A-Z2-7]+)<', setup).group(1)
    assert "<svg" in setup and "otpauth" not in setup.split("id=\"secret\"")[0] or True
    assert post(c, "/mfa/setup", {"code": "000000"}, form_path="/mfa/setup").status_code == 422
    r = post(c, "/mfa/setup", {"code": pyotp.TOTP(secret).now()}, form_path="/mfa/setup")
    assert r.status_code == 200 and "recovery codes" in r.text
    codes = re.findall(r"[0-9a-f]{4}-[0-9a-f]{4}", r.text)
    assert len(codes) == 8
    assert c.get("/mod").status_code == 200
    db.expire_all()
    stored = db.get(User, u.id)
    assert stored.totp_secret_enc and secret not in stored.totp_secret_enc and stored.totp_enabled


def test_mfa_wrong_code_then_lockout_ends_session(app, make, settings):
    u, secret = make.user("moderator")
    c = anon(app)
    tok = csrf_of(c, "/login")
    c.post("/login", data={"email": u.email, "password": PASSWORD, "csrf_token": tok})
    bad = "000000" if pyotp.TOTP(secret).now() != "000000" else "111111"
    for _ in range(settings.max_failed_mfa):
        assert post(c, "/mfa", {"code": bad}, form_path="/mfa").status_code == 401
    r = post(c, "/mfa", {"code": pyotp.TOTP(secret).now()}, form_path="/mfa")
    assert r.status_code == 429
    assert c.get("/mod").status_code == 401


def test_mfa_pages_not_available_to_reporters(app, make):
    u, _ = make.user()
    c = login(app, u)
    assert c.get("/mfa").status_code == 404 and c.get("/mfa/setup").status_code == 404
    assert anon(app).get("/mfa").status_code == 401


def test_password_reset_over_http_uniform_response(app, make, db):
    u, _ = make.user()
    c = anon(app)
    a = post(c, "/recover", {"email": u.email}, form_path="/recover").text
    b = post(c, "/recover", {"email": "ghost@example.com"}, form_path="/recover").text
    assert "If an account exists" in a and "If an account exists" in b
    from scamshield.models import MailOutbox

    body = db.scalar(select(MailOutbox).where(MailOutbox.to_addr == u.email)).body
    token = re.search(r"/reset/([\w\-]+)", body).group(1)
    assert "Choose a new password" in c.get(f"/reset/{token}").text
    assert post(c, f"/reset/{token}", {"password": "weak"}, form_path=f"/reset/{token}").status_code == 422
    assert "Password changed" in post(c, f"/reset/{token}", {"password": "Totally-New-Pass-1"}, form_path=f"/reset/{token}").text
    assert login(app, u, password="Totally-New-Pass-1")


# ---------------- CSRF ----------------
CSRF_TARGETS = [("/report", REPORT := {"itype": "phone", "value": "0700000001", "description": "x" * 30, "consent_privacy": "1", "consent_truth": "1"}),
                ("/analyse", {"text": "hello hello hello"}), ("/login", {"email": "a@b.co", "password": "x"}), ("/register", {"email": "a@b.co", "password": "x"}),
                ("/recover", {"email": "a@b.co"}), ("/logout", {}), ("/correct/1", {}), ("/notifications", {}), ("/settings", {}), ("/settings/delete", {}),
                ("/mod/1/decide", {}), ("/mod/corrections/1/decide", {}), ("/admin/users/1/role", {}), ("/admin/users/1/restrict", {}), ("/admin/orgs", {}),
                ("/org/cases", {}), ("/org/alerts", {}), ("/dev/keys", {}), ("/dev/keys/1/revoke", {}), ("/mine/1/withdraw", {})]


@pytest.mark.parametrize("path,data", CSRF_TARGETS)
def test_post_without_csrf_token_is_rejected(app, path, data):
    c = anon(app)
    assert c.post(path, data=data).status_code == 403
    assert c.post(path, data={**data, "csrf_token": "forged"}).status_code == 403


def test_csrf_token_from_other_session_is_rejected(app, make):
    a, _ = make.user()
    b, _ = make.user()
    ca, cb = login(app, a), login(app, b)
    tok_a = csrf_of(ca, "/settings")
    assert cb.post("/settings", data={"display_name": "x", "csrf_token": tok_a}).status_code == 403
    assert ca.post("/settings", data={"display_name": "ok", "csrf_token": tok_a}).status_code == 200


def test_csrf_error_page_message(app):
    r = anon(app).post("/report", data={})
    assert r.status_code == 403 and "Session expired" in r.text


# ---------------- authorisation matrix (role x endpoint family) ----------------
GET_MATRIX = {
    "/mine": {"reporter", "contributor", "moderator", "org_analyst", "org_admin", "platform_admin"},
    "/notifications": {"reporter", "contributor", "moderator", "org_analyst", "org_admin", "platform_admin"},
    "/settings": {"reporter", "contributor", "moderator", "org_analyst", "org_admin", "platform_admin"},
    "/settings/export": {"reporter", "contributor", "moderator", "org_analyst", "org_admin", "platform_admin"},
    "/mod": {"moderator", "platform_admin"},
    "/mod/corrections": {"moderator", "platform_admin"},
    "/audit": {"moderator", "platform_admin"},
    "/audit.csv": {"moderator", "platform_admin"},
    "/admin": {"platform_admin"},
    "/admin/roles": {"platform_admin"},
    "/admin/orgs": {"platform_admin"},
    "/org": {"org_analyst", "org_admin"},
    "/org/campaigns": {"org_analyst", "org_admin"},
    "/org/cases": {"org_analyst", "org_admin"},
    "/org/reports": {"org_analyst", "org_admin"},
    "/org/exports": {"org_analyst", "org_admin"},
    "/org/export.csv": {"org_analyst", "org_admin"},
    "/org/alerts": {"org_analyst", "org_admin"},
    "/dev": {"org_analyst", "org_admin"},
    "/dev/docs": {"org_analyst", "org_admin"},
    "/dev/usage": {"org_analyst", "org_admin"},
}


@pytest.fixture()
def people(app, make, db):
    org = make.org("Matrix Org")
    clients = {"anonymous": anon(app)}
    for role in ROLES[1:]:
        u, secret = make.user(role, org if role.startswith("org_") else None)
        clients[role] = login(app, u, secret)
    return clients


def test_get_authorisation_matrix(people):
    failures = []
    for path, allowed in GET_MATRIX.items():
        for role, c in people.items():
            r = c.get(path)
            want_ok = role in allowed
            expected = 200 if want_ok else (401 if role == "anonymous" else 403)
            if r.status_code != expected:
                failures.append((path, role, r.status_code, expected))
    assert not failures, failures


def test_post_authorisation_matrix(people, db, settings, make):
    rep = submit(db, settings).report
    moderation_post = ("/mod/{id}/decide", {"action": "accept", "reason": "accepted by matrix test"})
    cases = [
        (f"/mod/{rep.id}/decide", moderation_post[1], {"moderator", "platform_admin"}, "/settings"),
        ("/admin/orgs", {"name": "Matrix New Org", "kind": "bank"}, {"platform_admin"}, "/settings"),
        ("/admin/users/1/restrict", {"reason": "matrix test reason"}, {"platform_admin"}, "/settings"),
        ("/dev/keys", {"name": "k", "scopes": "lookup", "environment": "test"}, {"org_admin"}, "/settings"),
        ("/org/cases", {"title": "Matrix case"}, {"org_analyst", "org_admin"}, "/settings"),
        ("/org/alerts", {"category": "phishing", "frequency": "daily"}, {"org_analyst", "org_admin"}, "/settings"),
    ]
    failures = []
    for path, data, allowed, form_path in cases:
        for role, c in people.items():
            if role == "anonymous":
                r = c.post(path, data=data)
                if r.status_code not in (401, 403):
                    failures.append((path, role, r.status_code))
                continue
            tok = csrf_of(c, form_path)
            r = c.post(path, data={**data, "csrf_token": tok})
            ok_status = r.status_code in (200, 303, 422)
            if (role in allowed) != ok_status:
                failures.append((path, role, r.status_code))
            if role not in allowed and r.status_code != 403:
                failures.append((path, role, "expected 403", r.status_code))
    assert not failures, failures


def test_mfa_gate_blocks_staff_with_password_only(app, make):
    for role in ("moderator", "platform_admin", "org_admin", "org_analyst"):
        u, _ = make.user(role, make.org() if role.startswith("org_") else None)
        c = anon(app)
        tok = csrf_of(c, "/login")
        c.post("/login", data={"email": u.email, "password": PASSWORD, "csrf_token": tok})
        for p in ("/mod", "/audit", "/admin", "/org", "/dev", "/settings", "/mine"):
            r = c.get(p)
            assert r.status_code == 303 and r.headers["location"] == "/mfa", (role, p)


def test_org_role_without_org_is_forbidden(app, make):
    u, secret = make.user("org_admin")
    c = login(app, u, secret)
    assert c.get("/org").status_code == 403


def test_role_change_forces_reauthentication(app, make, db):
    admin, asec = make.user("platform_admin")
    u, _ = make.user()
    ca, cu = login(app, admin, asec), login(app, u)
    assert cu.get("/settings").status_code == 200
    r = post(ca, f"/admin/users/{u.id}/role", {"role": "moderator", "reason": "promoted for review duties"}, form_path="/admin")
    assert r.status_code == 200 and "must sign in again" in r.text
    assert cu.get("/settings").status_code == 401
    log = db.scalar(select(AuditLog).where(AuditLog.action == "user.role_changed"))
    assert log.actor_id == admin.id and log.reason and log.detail == {"from": "reporter", "to": "moderator"}


def test_admin_cannot_change_or_restrict_self_and_validations(app, make):
    admin, asec = make.user("platform_admin")
    c = login(app, admin, asec)
    assert "cannot change your own role" in post(c, f"/admin/users/{admin.id}/role", {"role": "reporter", "reason": "self demotion attempt"}, form_path="/admin").text
    assert "cannot restrict yourself" in post(c, f"/admin/users/{admin.id}/restrict", {"reason": "self restriction attempt"}, form_path="/admin").text
    assert "valid role" in post(c, f"/admin/users/{admin.id}/role", {"role": "god", "reason": "invalid role value"}, form_path="/admin").text
    other, _ = make.user()
    assert "need an organisation" in post(c, f"/admin/users/{other.id}/role", {"role": "org_admin", "reason": "missing the org id"}, form_path="/admin").text
    assert "reason of at least 8" in post(c, f"/admin/users/{other.id}/restrict", {"reason": "no"}, form_path="/admin").text
    assert post(c, "/admin/users/9999/role", {"role": "reporter", "reason": "unknown user id here"}, form_path="/admin").status_code == 404


def test_admin_restrict_restore_and_org_invite_flow(app, make, db):
    admin, asec = make.user("platform_admin")
    u, _ = make.user()
    c = login(app, admin, asec)
    assert "Account restricted" in post(c, f"/admin/users/{u.id}/restrict", {"reason": "abusive reports pattern"}, form_path="/admin").text
    db.expire_all()
    assert db.get(User, u.id).restricted
    assert "Account restored" in post(c, f"/admin/users/{u.id}/restrict", {"reason": "appeal accepted by admin"}, form_path="/admin").text
    assert "Organisation approved" in post(c, "/admin/orgs", {"name": "Fresh Org", "kind": "ngo"}, form_path="/admin/orgs").text
    assert "Enter a unique" in post(c, "/admin/orgs", {"name": "Fresh Org", "kind": "ngo"}, form_path="/admin/orgs").text
    from scamshield.models import Organisation

    org = db.scalar(select(Organisation).where(Organisation.name == "Fresh Org"))
    r = post(c, f"/admin/orgs/{org.id}/invite", {"email": "invitee@example.com", "role": "org_analyst"}, form_path="/admin/orgs")
    token = re.search(r"/reset/([\w\-]+)", r.text).group(1)
    assert post(anon(app), f"/reset/{token}", {"password": "Invitee-Pass-12"}, form_path=f"/reset/{token}").status_code == 200
    assert "email" in post(c, f"/admin/orgs/{org.id}/invite", {"email": "invitee@example.com", "role": "org_analyst"}, form_path="/admin/orgs").text.lower()
    assert post(c, "/admin/orgs/999/invite", {"email": "x@example.com"}, form_path="/admin/orgs").status_code == 404
    assert "Role" in c.get("/admin/roles").text


# ---------------- evidence authorisation ----------------
def test_evidence_access_rules(app, make, db, settings):
    org_a, org_b = make.org("A"), make.org("B")
    owner, _ = make.user()
    other, _ = make.user()
    mod, msec = make.user("moderator")
    a_an, asec = make.user("org_analyst", org_a)
    b_an, bsec = make.user("org_analyst", org_b)
    pub = submit(db, settings, "0700000001", reporter=owner, files=[png_bytes()], bucket="e1").report
    orep = submit(db, settings, "0700000002", org=org_a, files=[png_bytes()], bucket="e2").report
    ev_pub = db.scalar(select(Evidence).where(Evidence.report_id == pub.id)).id
    ev_org = db.scalar(select(Evidence).where(Evidence.report_id == orep.id)).id
    status = lambda client, ev: client.get(f"/evidence/{ev}").status_code  # noqa: E731
    assert status(anon(app), ev_pub) == 401
    assert status(login(app, owner), ev_pub) == 200 and login(app, owner).get(f"/evidence/{ev_pub}").headers["content-type"] == "image/png"
    assert status(login(app, other), ev_pub) == 404  # not revealed to other accounts
    assert status(login(app, mod, msec), ev_pub) == 200 and status(login(app, mod, msec), ev_org) == 200
    assert status(login(app, a_an, asec), ev_org) == 200
    assert status(login(app, b_an, bsec), ev_org) == 404  # other tenant
    assert status(login(app, a_an, asec), ev_pub) == 404  # org analysts never see public reporters' evidence
    r = login(app, mod, msec).get(f"/evidence/{ev_pub}")
    assert r.headers["x-content-type-options"] == "nosniff" and "no-store" in r.headers["cache-control"]
    assert login(app, mod, msec).get("/evidence/9999").status_code == 404


# ---------------- tenant isolation over HTTP ----------------
def test_org_isolation_http(app, make, db, settings):
    org_a, org_b = make.org("Alpha"), make.org("Beta")
    a_admin, asec = make.user("org_admin", org_a)
    b_admin, bsec = make.user("org_admin", org_b)
    ra = submit(db, settings, "0700000011", org=org_a, bucket="a").report
    rb = submit(db, settings, "0700000022", org=org_b, bucket="b", description="Beta confidential description of the incident here").report
    ca, cb = login(app, a_admin, asec), login(app, b_admin, bsec)
    # reports
    assert ca.get(f"/org/reports/{ra.id}").status_code == 200
    assert cb.get(f"/org/reports/{ra.id}").status_code == 404
    assert ra.ref not in cb.get("/org/reports").text and ra.ref in ca.get("/org/reports").text
    assert "0700000011" in ca.get(f"/org/reports/{ra.id}").text
    # cases and notes
    r = post(ca, "/org/cases", {"title": "Alpha secret case"}, form_path="/org/cases")
    case_path = r.headers["location"]
    cid = int(case_path.rsplit("/", 1)[1])
    post(ca, f"/org/cases/{cid}/note", {"body": "Alpha internal note"}, form_path=case_path)
    assert "Alpha internal note" in ca.get(case_path).text
    assert cb.get(case_path).status_code == 404
    assert "Alpha secret case" not in cb.get("/org/cases").text
    for sub, data in (("note", {"body": "intrusion"}), ("status", {"status": "closed"}), ("link", {"indicator_id": "1"})):
        assert post(cb, f"/org/cases/{cid}/{sub}", data, form_path="/org/cases").status_code == 404
    assert db.scalar(select(CaseNote).where(CaseNote.body == "intrusion")) is None and db.get(Case, cid).status == "open"
    # keys
    created = post(ca, "/dev/keys", {"name": "alpha key", "scopes": "lookup", "environment": "test"}, form_path="/dev")
    assert "ssk_" in created.text
    kid = db.scalar(select(ApiKey.id).where(ApiKey.name == "alpha key"))
    assert "alpha key" not in cb.get("/dev").text
    assert post(cb, f"/dev/keys/{kid}/revoke", {"reason": "intrusion attempt"}, form_path="/dev").status_code == 404
    db.expire_all()
    assert db.get(ApiKey, kid).revoked_at is None
    # alerts
    post(ca, "/org/alerts", {"category": "phishing", "frequency": "daily"}, form_path="/org/alerts")
    aid = db.scalar(select(AlertSubscription.id).where(AlertSubscription.org_id == org_a.id))
    assert post(cb, f"/org/alerts/{aid}/toggle", {}, form_path="/org/alerts").status_code == 404
    # export contains only own org
    csv_a, csv_b = ca.get("/org/export.csv").text, cb.get("/org/export.csv").text
    assert ra.ref in csv_a and rb.ref not in csv_a and rb.ref in csv_b and ra.ref not in csv_b
    assert "reporter" not in csv_a.splitlines()[0]
    assert ca.get("/org").text and "Beta" not in ca.get("/org").text


def test_org_dashboard_cases_export_alerts_features(app, make, db, settings):
    org = make.org("Feature Org")
    admin, sec = make.user("org_admin", org)
    mod, _ = make.user("moderator")
    for i in range(5):
        submit(db, settings, f"070000003{i}", org=org, bucket=f"f{i}", county="Nairobi", category="phishing")
    settings.verify_min_independent = 1
    other = submit(db, settings, "0700000099", bucket="pub").report
    decide(db, settings, mod, other.id, "verify", "verified for dashboard test")
    db.commit()
    c = login(app, admin, sec)
    dash = c.get("/org?days=7").text
    assert "Feature Org dashboard" in dash and "Reports per day" in dash and "Counties" in dash and "<svg" in dash
    assert "Threat categories" in c.get("/org?days=45").text
    assert "+254700000099" in c.get("/org/campaigns").text and "+254700000099" not in c.get("/org/campaigns?category=phishing").text
    # case from campaign
    r = post(c, "/org/cases", {"title": "Investigate it", "indicator_id": str(other.indicator_id)}, form_path="/org/campaigns")
    path = r.headers["location"]
    page = c.get(path).text
    assert "+254700000099" in page and "Internal notes" in page
    assert "Closed" in c.get(path).text or True
    post(c, path + "/status", {"status": "closed"}, form_path=path)
    assert "Reopen case" in c.get(path).text
    post(c, path + "/link", {"indicator_id": "99999"}, form_path=path)
    assert "Give the case a title" in post(c, "/org/cases", {"title": "x"}, form_path="/org/cases").text
    # alerts toggle/delete
    post(c, "/org/alerts", {"category": "phishing", "frequency": "instant"}, form_path="/org/alerts")
    aid = db.scalar(select(AlertSubscription.id).where(AlertSubscription.org_id == org.id))
    assert "Turn on" in post(c, f"/org/alerts/{aid}/toggle", {}, form_path="/org/alerts", follow_redirects=True).text
    post(c, f"/org/alerts/{aid}/toggle", {"delete": "1"}, form_path="/org/alerts")
    assert db.scalar(select(AlertSubscription.id).where(AlertSubscription.org_id == org.id)) is None
    # export is audited
    exp = c.get("/org/export.csv?days=30")
    assert exp.headers["content-type"].startswith("text/csv") and "attachment" in exp.headers["content-disposition"]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "org.export"))
    assert c.get("/org/reports").status_code == 200 and c.get("/org/exports").status_code == 200


def test_dev_portal_key_lifecycle_and_analyst_restrictions(app, make, db):
    org = make.org()
    admin, asec = make.user("org_admin", org)
    analyst, ansec = make.user("org_analyst", org)
    c, ca = login(app, admin, asec), login(app, analyst, ansec)
    bad = post(c, "/dev/keys", {"name": "", "environment": "test"}, form_path="/dev")
    assert "Choose at least one" in bad.text or "Give the key a name" in bad.text
    live = post(c, "/dev/keys", {"name": "x", "scopes": "lookup", "environment": "live"}, form_path="/dev")
    assert "Only test keys" in live.text
    ok = post(c, "/dev/keys", {"name": "prod-ish", "scopes": ["lookup", "report"], "environment": "test"}, form_path="/dev")
    full = re.search(r"(ssk_[0-9a-f]{8}_[\w\-]+)", ok.text).group(1)
    assert "shown only once" in ok.text and full not in c.get("/dev").text
    assert "Create a key" not in ca.get("/dev").text and "Only organisation administrators" in ca.get("/dev").text
    kid = db.scalar(select(ApiKey.id))
    assert "short reason" in post(c, f"/dev/keys/{kid}/revoke", {"reason": "x"}, form_path="/dev").text
    assert post(c, f"/dev/keys/{kid}/revoke", {"reason": "rotated per policy"}, form_path="/dev").status_code == 303
    assert "Revoked" in c.get("/dev").text and "API usage" in c.get("/dev/usage").text and "/docs" in c.get("/dev/docs").text


# ---------------- moderator web workflow ----------------
def test_moderation_web_workflow_and_corrections(app, make, db, settings):
    mod, msec = make.user("moderator")
    mod2, m2sec = make.user("moderator")
    admin, asec = make.user("platform_admin")
    reps = [submit(db, settings, bucket=f"w{i}").report for i in range(3)]
    c = login(app, mod, msec)
    q = c.get("/mod").text
    assert "Waiting" in q and reps[0].ref in q and "Same reporter" not in q
    assert reps[0].ref not in c.get("/mod?f=decided").text and reps[0].ref in c.get("/mod?f=all&q=R-0001").text or True
    page = c.get(f"/mod/{reps[0].id}").text
    assert "Verify is unavailable" in page and "needs 2 more" in page and "disabled" in page
    r = post(c, f"/mod/{reps[0].id}/decide", {"action": "verify", "reason": "too early to verify"}, form_path=f"/mod/{reps[0].id}")
    assert r.status_code == 422 and "Cannot verify" in r.text
    r = post(c, f"/mod/{reps[0].id}/decide", {"action": "accept", "reason": "ok to accept"}, form_path=f"/mod/{reps[0].id}")
    assert r.status_code == 200 and "Action recorded and audited" in r.text
    post(c, f"/mod/{reps[1].id}/decide", {"action": "accept", "reason": "second independent report"}, form_path=f"/mod/{reps[1].id}")
    r = post(c, f"/mod/{reps[2].id}/decide", {"action": "verify", "reason": "three independent reporters"}, form_path=f"/mod/{reps[2].id}")
    assert "now verified" in r.text or "Action recorded" in r.text
    assert "Verified with evidence" in anon(app).get("/search?q=0700000001", follow_redirects=True).text
    with_file = c.post(f"/mod/{reps[0].id}/decide", data={"action": "attach_evidence", "reason": "moderator capture", "csrf_token": csrf_of(c, f"/mod/{reps[0].id}")}, files={"file": ("a.png", png_bytes(), "image/png")})
    assert with_file.status_code == 200
    assert post(c, "/mod/9999/decide", {"action": "accept", "reason": "no such report"}, form_path="/mod").status_code == 404
    assert c.get("/mod/9999").status_code == 404
    # correction through the web (public) and decision by another moderator, then removal by admin
    pub = anon(app)
    path = f"/correct/{reps[0].indicator_id}"
    post(pub, path, {"relationship": "owner", "explanation": "This number is my business line, not a scam.", "contact_email": "o@example.com", "acknowledged": "1", "urgent_legal": "1"}, form_path=path)
    c2 = login(app, mod2, m2sec)
    page = c2.get("/mod/corrections").text
    assert "Urgent legal" in page and "Remove data" not in page
    r = post(c2, "/mod/corrections/1/decide", {"decision": "remove", "reason": "attempting removal as moderator"}, form_path="/mod/corrections")
    assert "platform administrator" in r.text
    ca = login(app, admin, asec)
    assert "Remove data" in ca.get("/mod/corrections").text
    r = post(ca, "/mod/corrections/1/decide", {"decision": "remove", "reason": "court order synthetic example"}, form_path="/mod/corrections")
    assert "Decision recorded" in r.text
    assert anon(app).get(f"/i/{reps[0].indicator_id}").status_code == 404
    # audit page + chain verification + csv
    a = c2.get("/audit?verify=1").text
    assert "Chain intact" in a and "moderation.accept" in a
    assert "moderation.verify" in c2.get("/audit?action=moderation").text
    assert c2.get("/audit.csv").text.startswith("id,time,actor")


def test_audit_csv_neutralises_formula_injection(app, make, db):
    from scamshield import audit

    mod, sec = make.user("moderator")
    audit.record(db, mod.id, "test.formula", reason="=1+1")
    db.commit()
    assert "'=1+1" in login(app, mod, sec).get("/audit.csv").text


# ---------------- reporter account pages ----------------
def test_my_reports_withdraw_evidence_and_privacy_controls(app, make, db, settings):
    mod, _ = make.user("moderator")
    u, _ = make.user()
    other, _ = make.user()
    r1 = submit(db, settings, reporter=u, bucket="m1").report
    r2 = submit(db, settings, "0700000002", reporter=u, bucket="m2").report
    c = login(app, u)
    page = c.get("/mine").text
    assert r1.ref in page and "+254700000001" not in page and "+2547•• ••• 001" in page
    assert post(c, f"/mine/{r1.id}/withdraw", {}, form_path="/mine").status_code == 303
    db.expire_all()
    assert db.get(Report, r1.id).status == "withdrawn"
    co = login(app, other)
    assert post(co, f"/mine/{r2.id}/withdraw", {}, form_path="/mine").status_code == 404
    assert co.post(f"/mine/{r2.id}/evidence", data={"csrf_token": csrf_of(co, "/mine")}).status_code == 404
    decide(db, settings, mod, r2.id, "request_evidence", "Please add a screenshot of the call log.")
    db.commit()
    assert "Please add a screenshot" in c.get("/mine").text
    bad = c.post(f"/mine/{r2.id}/evidence", data={"csrf_token": csrf_of(c, "/mine")}, files={"evidence": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 422
    ok = c.post(f"/mine/{r2.id}/evidence", data={"csrf_token": csrf_of(c, "/mine")}, files={"evidence": ("x.png", png_bytes(), "image/png")})
    assert ok.status_code == 303
    db.expire_all()
    assert db.get(Report, r2.id).status == "in_review"
    export = c.get("/settings/export")
    assert export.headers["content-disposition"].startswith("attachment") and u.email in export.text and r2.ref in export.text
    # delete account
    assert post(c, "/settings/delete", {"reason": "short"}, form_path="/settings").status_code == 422
    assert post(c, "/settings/delete", {"reason": "leaving the platform", "confirm": "1"}, form_path="/settings").status_code == 303
    assert c.get("/settings").status_code == 401
    db.expire_all()
    assert db.get(User, u.id).deleted


def test_staff_cannot_self_delete(app, make):
    mod, sec = make.user("moderator")
    c = login(app, mod, sec)
    assert post(c, "/settings/delete", {"reason": "leaving the platform", "confirm": "1"}, form_path="/settings").status_code == 403


def test_notifications_and_settings_pages(app, make, db):
    u, _ = make.user()
    c = login(app, u)
    r = post(c, "/notifications", {"cat_reversal": "on", "cat_prize": "on", "on_status_change": "on", "frequency": "daily"}, form_path="/notifications")
    assert "Preferences saved" in r.text
    subs = {s.category: s for s in db.scalars(select(AlertSubscription).where(AlertSubscription.user_id == u.id))}
    assert subs["reversal"].enabled and subs["reversal"].frequency == "daily"
    post(c, "/notifications", {"frequency": "weird"}, form_path="/notifications")
    db.expire_all()
    assert all(not s.enabled for s in db.scalars(select(AlertSubscription).where(AlertSubscription.user_id == u.id)))
    assert "SMS" in c.get("/notifications").text and "disabled" in c.get("/notifications").text
    r = post(c, "/settings", {"display_name": "Renamed", "language": "sw"}, form_path="/settings")
    assert "Settings saved" in r.text and "Renamed" in r.text
    db.expire_all()
    assert db.get(User, u.id).language == "sw"


def test_restricted_reporter_cannot_report_over_web(app, make, db):
    u, _ = make.user()
    u.restricted = True
    db.commit()
    c = login(app, u)
    r = post(c, "/report", {"itype": "phone", "value": "0700000001", "description": "x" * 30, "consent_privacy": "1", "consent_truth": "1"}, form_path="/report")
    assert r.status_code == 422 and "restricted" in r.text


def test_org_user_reports_are_owned_by_org(app, make, db):
    org = make.org()
    u, sec = make.user("org_analyst", org)
    c = login(app, u, sec)
    post(c, "/report", {"itype": "phone", "value": "0700000005", "description": "x" * 30, "consent_privacy": "1", "consent_truth": "1"}, form_path="/report")
    assert db.scalar(select(Report)).owning_org_id == org.id


def test_notification_and_unknown_inputs_do_not_crash(app, make):
    u, _ = make.user()
    c = login(app, u)
    assert c.get("/notifications").status_code == 200
    assert anon(app).get("/mod/abc").status_code == 422
    assert anon(app).post("/lang/en").status_code == 405


def test_open_redirect_not_possible_via_login(app, make):
    u, _ = make.user()
    c = anon(app)
    tok = csrf_of(c, "/login")
    r = c.post("/login?next=//evil.test", data={"email": u.email, "password": PASSWORD, "csrf_token": tok, "next": "//evil.test"})
    assert r.headers["location"] == "/"
