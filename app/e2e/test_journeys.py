from __future__ import annotations

import re
import time

import httpx
import pyotp
import pytest
from conftest import BASE, PASSWORD

pytestmark = pytest.mark.e2e
DESC = "Someone called and asked me to send money back for a mistaken transfer."


def submit_report(page, itype: str, value: str, desc: str = DESC, category: str = "reversal", message: str | None = None):
    page.goto("/report")
    page.get_by_label("Phone number").check() if itype == "phone" else page.get_by_label("Website or link").check()
    page.get_by_role("button", name="Next").click()
    page.fill("#f-value", value)
    page.select_option("#f-category", category)
    page.fill("#f-description", desc)
    page.get_by_role("button", name="Next").click()  # details
    page.get_by_role("button", name="Next").click()  # evidence
    page.check("#f-consent_privacy")
    page.check("#f-consent_truth")
    page.get_by_role("button", name="Next").click()
    page.get_by_role("button", name="Send report").first.click()
    page.wait_for_url(re.compile(r"/report/done"))
    return page.locator("#ref").inner_text()


def sign_in(page, email: str, secret: str | None = None):
    page.goto("/login")
    page.fill("#email", email)
    page.fill("#password", PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    if secret:
        page.wait_for_url(re.compile(r"/mfa"))
        page.fill("#code", pyotp.TOTP(secret).now())
        page.get_by_role("button", name="Verify").click()
    page.wait_for_load_state()


def decide(page, report_id: int, action: str, reason: str, **extra):
    page.goto(f"/mod/{report_id}")
    page.locator("details.act-group").evaluate_all("els => els.forEach(e => { e.open = true; })")  # groups are collapsed on phones
    page.fill("#reason", reason)
    if "target" in extra:
        page.select_option("#target", str(extra["target"]))
    page.locator(f'button[name="action"][value="{action}"]').click()
    page.wait_for_load_state()


def report_id(ref: str) -> int:
    return int(ref.split("-")[1])


def test_report_to_moderation_to_public_verified_search(new_page, staff):
    number = "0700 111 201"
    refs = []
    for i in range(3):  # three different devices/people
        p = new_page(ua=f"e2e-device-{i}-{time.time()}")
        refs.append(submit_report(p, "phone", number))
        assert not p.errors
    email, secret = staff.create("moderator")
    mod = new_page(ua="e2e-moderator")
    sign_in(mod, email, secret)
    mod.goto("/mod")
    assert mod.get_by_text(refs[0]).first.is_visible()
    # verify is refused until the policy is met (button disabled with reason)
    mod.goto(f"/mod/{report_id(refs[2])}")
    assert mod.locator('button[value="verify"]').is_disabled()
    assert "needs" in mod.locator(".notice.warn").first.inner_text()
    decide(mod, report_id(refs[0]), "accept", "Consistent with the other reports")
    decide(mod, report_id(refs[1]), "accept", "Second independent reporter")
    decide(mod, report_id(refs[2]), "verify", "Three independent reporters agree")
    assert "Action recorded" in mod.content()
    public = new_page(ua="e2e-public")
    public.goto("/")
    public.fill("#q", number)
    public.get_by_role("button", name="Search").click()
    public.wait_for_load_state()
    body = public.inner_text("main")
    assert "Verified with evidence" in body and "3 independent reports" in body and "+254700111201" in body
    public.get_by_text("+254700111201").first.click()
    assert "Review history" in public.inner_text("main") and "Request a correction" in public.inner_text("main")
    assert "/evidence/" not in public.content()
    assert not public.errors and not mod.errors


def test_same_device_reports_do_not_become_independent(new_page, staff):
    number = "0700 111 202"
    refs = [submit_report(new_page(ua="e2e-same-device"), "phone", number) for _ in range(3)]
    email, secret = staff.create("moderator")
    mod = new_page(ua="e2e-moderator-2")
    sign_in(mod, email, secret)
    decide(mod, report_id(refs[0]), "accept", "Accepting the first report")
    decide(mod, report_id(refs[1]), "accept", "Accepting the second report")
    mod.goto(f"/mod/{report_id(refs[2])}")
    assert mod.locator('button[value="verify"]').is_disabled()
    assert "Same reporter or device" in mod.inner_text("main")


def test_duplicate_merge(new_page, staff):
    ref_a = submit_report(new_page(ua="e2e-merge-a"), "url", "https://scam-one.example/pay", category="phishing", desc="Fake payment page asking for card details.")
    ref_b = submit_report(new_page(ua="e2e-merge-b"), "url", "scam-two.example/pay", category="phishing", desc="Same fake payment page, different domain name.")
    email, secret = staff.create("moderator")
    mod = new_page(ua="e2e-moderator-3")
    sign_in(mod, email, secret)
    decide(mod, report_id(ref_a), "accept", "First variant of the fake page")
    mod.goto(f"/mod/{report_id(ref_b)}")
    target_value = mod.locator("#target option", has_text="scam-one.example").first.get_attribute("value")
    decide(mod, report_id(ref_b), "merge", "Same campaign, merge into first domain", target=target_value)
    assert "Action recorded" in mod.content()
    mod.goto(f"/mod/{report_id(ref_b)}")
    assert "Merged" in mod.inner_text("main")
    public = new_page(ua="e2e-public-merge")
    public.goto("/search?q=scam-one.example/pay")
    assert "2 independent reports" in public.inner_text("main") or "independent report" in public.inner_text("main")
    public.goto("/search?q=scam-two.example/pay")
    assert "No published record" in public.inner_text("main")


def test_correction_challenge_flow(new_page, staff):
    refs = [submit_report(new_page(ua=f"e2e-corr-{i}"), "phone", "0700 111 204") for i in range(3)]
    email, secret = staff.create("moderator")
    email2, secret2 = staff.create("moderator")
    m1 = new_page(ua="e2e-mod-c1")
    sign_in(m1, email, secret)
    for r in refs[:2]:
        decide(m1, report_id(r), "accept", "Accepting for correction journey")
    decide(m1, report_id(refs[2]), "verify", "Three independent reporters")
    owner = new_page(ua="e2e-owner")
    owner.goto("/search?q=0700111204")
    owner.get_by_text("+254700111204").first.click()
    owner.get_by_role("link", name="Request a correction").first.click()
    owner.get_by_label("I own this number, website or account").check()
    owner.fill("#f-explanation", "This is my shop line, I never called anyone about reversals.")
    owner.fill("#f-contact_email", "owner@example.com")
    owner.check("#f-acknowledged")
    owner.get_by_role("button", name="Send request").click()
    assert "Correction request received" in owner.inner_text("main") and re.search(r"C-\d{4}", owner.inner_text("main"))
    owner.goto("/search?q=0700111204")
    assert "Disputed" in owner.inner_text("main")
    m2 = new_page(ua="e2e-mod-c2")
    sign_in(m2, email2, secret2)
    m2.goto("/mod/corrections")
    card = m2.locator("article", has_text="0700111204").first if m2.locator("article", has_text="0700111204").count() else m2.locator("article").last
    card.locator('input[name="reason"]').fill("Owner evidence reviewed, softening the record")
    card.get_by_role("button", name="Accept (soften record)").click()
    assert "Decision recorded" in m2.inner_text("main")
    owner.goto("/search?q=0700111204")
    body = owner.inner_text("main")
    assert "Reported, not verified" in body and "Disputed" not in body


def test_organisation_isolation(new_page, staff):
    a_email, a_secret = staff.create("org_admin", "E2E Org Alpha")
    b_email, b_secret = staff.create("org_admin", "E2E Org Beta")
    pa = new_page(ua="e2e-org-a")
    sign_in(pa, a_email, a_secret)
    ref = submit_report(pa, "url", "https://alpha-only.example/login", category="phishing", desc="Alpha customers reported a look-alike login page.")
    pa.goto("/org/reports")
    assert ref in pa.inner_text("main")
    link = pa.get_by_role("link", name=ref).get_attribute("href")
    pa.goto("/org/cases")
    pa.fill("#title", "Alpha private case")
    pa.get_by_role("button", name="Create case").click()
    case_url = pa.url
    pa.fill("#body", "Alpha internal note")
    pa.get_by_role("button", name="Add note").click()
    pb = new_page(ua="e2e-org-b")
    sign_in(pb, b_email, b_secret)
    pb.goto(link)
    assert "Page not found" in pb.inner_text("main")
    pb.goto(case_url)
    assert "Page not found" in pb.inner_text("main")
    pb.goto("/org/reports")
    assert ref not in pb.inner_text("main")
    csv = pb.request.get("/org/export.csv").text()
    assert ref not in csv
    assert ref in pa.request.get("/org/export.csv").text()
    assert pb.request.get("/org/cases").text().count("Alpha private case") == 0


def test_api_key_lifecycle_and_lookup(new_page, staff):
    email, secret = staff.create("org_admin", "E2E Org API")
    page = new_page(ua="e2e-dev")
    sign_in(page, email, secret)
    page.goto("/dev")
    page.fill("#name", "e2e key")
    page.get_by_label("report").check()
    page.get_by_role("button", name="Create key").click()
    key = re.search(r"ssk_[0-9a-f]{8}_[\w\-]+", page.locator("#newkey").inner_text()).group(0)
    assert "shown only once" in page.inner_text("main")
    # report via API then look it up (not yet public -> found false), unauthenticated -> 401
    h = {"Authorization": f"Bearer {key}"}
    r = httpx.post(f"{BASE}/api/v1/reports", headers=h, json={"type": "phone", "value": "0700111209", "description": "Reported by our fraud desk via API.", "category": "impersonation", "consent_privacy": True, "consent_truth": True})
    assert r.status_code == 201  # key has the default lookup scope plus the ticked report scope
    ref = r.json()["reference"]
    assert httpx.get(f"{BASE}/api/v1/reports/{ref}/status", headers=h).json()["indicator_status"] == "not_published"
    ok = httpx.get(f"{BASE}/api/v1/indicators/lookup", params={"value": "0700111209"}, headers=h)
    assert ok.status_code == 200 and ok.json()["found"] is False
    assert httpx.get(f"{BASE}/api/v1/indicators/lookup", params={"value": "0700111209"}).status_code == 401
    # revoke in the UI, key stops working
    page.goto("/dev")
    page.locator('input[name="reason"]').first.fill("rotated after e2e test")
    page.get_by_role("button", name="Revoke").first.click()
    page.wait_for_load_state()
    assert "Revoked" in page.inner_text("main")
    assert httpx.get(f"{BASE}/api/v1/indicators/lookup", params={"value": "0700111209"}, headers=h).status_code == 401
