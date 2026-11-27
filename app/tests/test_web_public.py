import re

from conftest import csrf_of, login, post
from fastapi.testclient import TestClient
from helpers import png_bytes, submit
from sqlalchemy import select

from scamshield.models import Correction, Indicator, Report
from scamshield.moderation import decide

REPORT = {"itype": "phone", "value": "0700 000 001", "category": "reversal", "description": "Someone called and asked me to send money back for a mistaken transfer.",
          "consent_privacy": "1", "consent_truth": "1"}


def anon(app):
    return TestClient(app, base_url="http://testserver", follow_redirects=False)


def test_pages_render_and_have_security_headers(client):
    for p in ("/", "/search", "/report", "/analyse", "/login", "/register", "/recover", "/about", "/healthz", "/openapi.json", "/docs", "/robots.txt"):
        r = client.get(p)
        assert r.status_code == 200, p
    r = TestClient(client.app).get("/")
    h = r.headers
    assert "script-src 'self'" in h["content-security-policy"] and "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY" and "no-store" in h["cache-control"]
    assert "ss_anon" in r.headers.get("set-cookie", "") and "HttpOnly" in r.headers["set-cookie"]
    assert "cdn" not in r.text.lower() and "googleapis" not in r.text
    assert client.get("/nope").status_code == 404 and client.get("/i/999").status_code == 404
    assert client.get("/healthz").json() == {"status": "ok"}


def test_docs_are_served_locally_without_cdn(client):
    html = client.get("/docs").text
    assert "/static/swagger/swagger-ui-bundle.js" in html and "cdn.jsdelivr" not in html
    spec = client.get("/openapi.json").json()
    for path in ("/api/v1/indicators/lookup", "/api/v1/reports", "/api/v1/reports/{ref}/status", "/api/v1/threat-intel", "/api/v1/org/analytics"):
        assert path in spec["paths"]
    assert client.get("/static/swagger/swagger-ui-bundle.js").status_code == 200


def test_report_submission_flow_and_confirmation(app, db):
    c = anon(app)
    r = post(c, "/report", REPORT, form_path="/report")
    assert r.status_code == 303 and r.headers["location"].startswith("/report/done?ref=R-")
    page = c.get(r.headers["location"]).text
    assert "Report received" in page and "R-0001" in page
    assert db.scalar(select(Report)).device_bucket and db.scalar(select(Indicator)).status == "pending"


def test_report_validation_errors_keep_input_and_show_summary(app):
    c = anon(app)
    r = post(c, "/report", {**REPORT, "value": "123", "description": "short", "consent_truth": ""}, form_path="/report")
    assert r.status_code == 422
    assert 'id="error-summary"' in r.text and "Check the value" in r.text and 'value="123"' in r.text
    assert "20 to 2,000" in r.text


def test_report_bad_date_and_amount(app):
    c = anon(app)
    r = post(c, "/report", {**REPORT, "incident_date": "garbage", "amount_kes": "abc"}, form_path="/report")
    assert r.status_code == 422 and "valid date" in r.text and "whole number" in r.text


def test_upload_abuse_over_http(app, db):
    c = anon(app)
    tok = csrf_of(c, "/report")
    bad = [("evidence", ("shell.png", b"<?php system($_GET['c']); ?>", "image/png"))]
    r = c.post("/report", data={**REPORT, "csrf_token": tok}, files=bad)
    assert r.status_code == 422 and "Only PNG, JPEG or WebP" in r.text
    svg = [("evidence", ("x.svg", b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>", "image/svg+xml"))]
    assert c.post("/report", data={**REPORT, "csrf_token": tok}, files=svg).status_code == 422
    many = [("evidence", (f"{i}.png", png_bytes(), "image/png")) for i in range(7)]
    r = c.post("/report", data={**REPORT, "csrf_token": tok}, files=many)
    assert r.status_code == 422 and "At most 5" in r.text
    assert db.scalar(select(Report)) is None  # nothing stored on failed submissions


def test_valid_upload_over_http_is_reencoded_and_stored_outside_web_root(app, db, settings):
    c = anon(app)
    tok = csrf_of(c, "/report")
    r = c.post("/report", data={**REPORT, "csrf_token": tok}, files=[("evidence", ("shot.png", png_bytes(), "image/png"))])
    assert r.status_code == 303
    files = list(settings.storage_dir.rglob("*.png"))
    assert len(files) == 1 and re.fullmatch(r"[a-f0-9]{32}\.png", files[0].name)
    assert client_static_404(app, files[0].name)


def client_static_404(app, name):
    return TestClient(app).get(f"/static/{name}").status_code == 404


def test_report_rate_limit(app, settings):
    settings.report_rate_per_hour = 3
    c = anon(app)
    codes = [post(c, "/report", {**REPORT, "value": f"07000000{i:02d}"}, form_path="/report").status_code for i in range(5)]
    assert codes[:3] == [303, 303, 303] and codes[3:] == [429, 429]


def test_search_exact_match_shows_status_but_lists_are_masked(app, db, settings, make):
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "accept", "accepted for search test")
    db.commit()
    c = anon(app)
    exact = c.get("/search", params={"q": "0700 000 001"}).text
    assert "+254700000001" in exact and "Reported, not verified" in exact and "independent report" in exact
    listing = c.get("/search").text
    assert "+2547•• ••• 001" in listing and "+254700000001" not in listing
    # partial text search must not reveal records (no enumeration)
    assert "No published record" not in c.get("/search", params={"q": "07000"}).text or "+254700000001" not in c.get("/search", params={"q": "07000"}).text
    none = c.get("/search", params={"q": "0799999999"}).text
    assert "No published record found" in none and "Not reported does not mean safe" in none
    bad = c.get("/search", params={"q": "!!!"}).text
    assert "does not look like" in bad


def test_record_page_masks_unless_exact_token_and_never_shows_evidence(app, db, settings, make):
    mod, _ = make.user("moderator")
    u, _ = make.user()
    r = submit(db, settings, reporter=u, files=[png_bytes()]).report
    decide(db, settings, mod, r.id, "accept", "accepted for record test")
    db.commit()
    c = anon(app)
    masked = c.get(f"/i/{r.indicator_id}").text
    assert "+2547•• ••• 001" in masked and "+254700000001" not in masked and "/evidence/" not in masked and u.email not in masked
    link = re.search(r'href="(/i/\d+\?v=[a-f0-9]+)"', c.get("/search", params={"q": "0700000001"}).text).group(1)
    assert "+254700000001" in c.get(link).text
    assert "+254700000001" not in c.get(f"/i/{r.indicator_id}?v=forged").text
    assert c.get(f"/i/{r.indicator_id}").status_code == 200


def test_pending_record_is_404_publicly_but_visible_to_staff(app, db, settings, make):
    r = submit(db, settings).report
    assert anon(app).get(f"/i/{r.indicator_id}").status_code == 404
    mod, secret = make.user("moderator")
    assert login(app, mod, secret).get(f"/i/{r.indicator_id}").status_code == 200


def test_analyse_page(app):
    c = anon(app)
    r = post(c, "/analyse", {"text": "URGENT your KCB account will be suspended confirm your PIN at http://kcb-login.top now"}, form_path="/analyse")
    assert r.status_code == 200 and "Several warning signs" in r.text and "<mark" in r.text and "not proof" in r.text
    assert post(c, "/analyse", {"text": "short"}, form_path="/analyse").status_code == 422


def test_analyse_rate_limit(app):
    c = anon(app)
    codes = [post(c, "/analyse", {"text": "hello there, how are you today friend"}, form_path="/analyse").status_code for _ in range(32)]
    assert codes.count(429) == 2


def test_correction_challenge_flow_over_http(app, db, settings, make):
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "accept", "accepted for correction test")
    db.commit()
    c = anon(app)
    path = f"/correct/{r.indicator_id}"
    bad = post(c, path, {"relationship": "owner", "explanation": "short", "contact_email": "x"}, form_path=path)
    assert bad.status_code == 422 and "at least 20" in bad.text
    ok = post(c, path, {"relationship": "owner", "explanation": "This is my shop number and it has been misreported.", "contact_email": "o@example.com", "acknowledged": "1"}, form_path=path)
    assert ok.status_code == 200 and "C-0001" in ok.text and "disputed" in ok.text
    assert "Disputed" in c.get("/search", params={"q": "0700000001"}).text
    assert db.scalar(select(Correction)).status == "open"
    assert c.get("/correct/999").status_code == 404 and post(c, "/correct/999", {}, form_path=path).status_code == 404


def test_correction_rate_limit(app, db, settings, make):
    settings.correction_rate_per_hour = 2
    mod, _ = make.user("moderator")
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "accept", "accepted for correction rate test")
    db.commit()
    c = anon(app)
    path = f"/correct/{r.indicator_id}"
    d = {"relationship": "owner", "explanation": "This is my shop number and it has been misreported.", "contact_email": "o@example.com", "acknowledged": "1"}
    assert [post(c, path, d, form_path=path).status_code for _ in range(3)] == [200, 200, 429]


# ---------------- XSS: user-controlled text is escaped everywhere it is rendered ----------------
XSS = "<script>alert('xss')</script><img src=x onerror=alert(1)>"


def assert_escaped(html: str):
    assert "<script>alert('xss')" not in html and "<img src=x onerror" not in html
    assert "&lt;script&gt;" in html or "&lt;img" in html


def test_xss_in_report_text_review_record_and_search(app, db, settings, make):
    mod, secret = make.user("moderator")
    c = anon(app)
    post(c, "/report", {**REPORT, "itype": "business", "value": XSS, "description": "Business name with markup: " + XSS}, form_path="/report")
    r = db.scalar(select(Report))
    m = login(app, mod, secret)
    assert_escaped(m.get(f"/mod/{r.id}").text)
    assert_escaped(m.get("/mod").text)
    decide(db, settings, mod, r.id, "accept", "accepted for xss test " + XSS)
    db.commit()
    assert_escaped(m.get(f"/i/{r.indicator_id}").text)
    assert_escaped(m.get("/audit").text)
    assert_escaped(m.get(f"/mod/{r.id}").text)


def test_xss_in_analyse_correction_and_message(app, db, settings, make):
    c = anon(app)
    out = post(c, "/analyse", {"text": XSS + " URGENT send KES 500 to till 123456 now"}, form_path="/analyse").text
    assert_escaped(out)
    mod, secret = make.user("moderator")
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "accept", "accepted for xss correction test")
    db.commit()
    path = f"/correct/{r.indicator_id}"
    post(c, path, {"relationship": "owner", "explanation": XSS + " padding text here", "contact_email": "o@example.com", "acknowledged": "1"}, form_path=path)
    assert_escaped(login(app, mod, secret).get("/mod/corrections").text)


def test_language_toggle_and_swahili_draft_notice(client):
    r = client.get("/lang/sw", headers={"referer": "http://testserver/about"})
    assert r.status_code == 200 and "Angalia" in client.get("/").text and "needs native review" in client.get("/").text
    client.get("/lang/en")
    assert "Angalia" not in client.get("/").text
    assert client.get("/lang/xx").status_code == 404
    r = client.get("/lang/sw", headers={"referer": "http://evil.test//x"}, follow_redirects=False)
    assert r.headers["location"].startswith("/") and not r.headers["location"].startswith("//")


def test_demo_banner_only_when_synthetic_data_present(app, db, settings, make):
    assert "Synthetic demonstration data" not in TestClient(app).get("/").text
    submit(db, settings)
    ind = db.scalar(select(Indicator))
    ind.origin = "synthetic test data"
    db.commit()
    app.state.reset_demo_flag()
    assert "Synthetic demonstration data" in TestClient(app).get("/").text
