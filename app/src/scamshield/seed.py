"""Seed command: SYNTHETIC demonstration data only.

Every record is labelled origin="synthetic test data". Phone numbers use obviously fake patterns,
domains use reserved names (example.com/.test/.invalid), and no real person or business appears.
Records are created through the real services so the audit trail and counts are genuine for the demo.
"""

from __future__ import annotations

import io
from datetime import timedelta
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import accounts, notify, orgs
from .config import Settings
from .corrections import submit_correction
from .models import AlertSubscription, Case, Indicator, Organisation, User, utcnow
from .moderation import decide
from .reports import SubmitInput, submit_report
from .security import encrypt_field, new_totp_secret
from .tenancy import TenantScope

ORIGIN = "synthetic test data"
DEMO_PASSWORD = "DemoPass-2026x"  # noqa: S105 - synthetic demo accounts only


def _png(label: str) -> bytes:
    img = Image.new("RGB", (480, 320), (240, 234, 221))
    d = ImageDraw.Draw(img)
    d.rectangle((10, 10, 470, 310), outline=(11, 90, 83), width=4)
    d.text((24, 24), "SYNTHETIC DEMONSTRATION IMAGE", fill=(168, 33, 26))
    d.text((24, 60), label, fill=(20, 32, 31))
    d.text((24, 100), "Not a real screenshot. Made for demo.", fill=(68, 83, 79))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _user(db: Session, settings: Settings, email: str, role: str, org: Organisation | None = None, name: str = "") -> User:
    u = accounts.register(db, email, DEMO_PASSWORD, name or email.split("@")[0], True, role=role, org_id=org.id if org else None, origin=ORIGIN)
    if role in settings.mfa_roles:
        secret = new_totp_secret()
        u.totp_secret_enc = encrypt_field(settings.secret_key, secret)
        u.totp_enabled = True
    return u


def seed(db: Session, settings: Settings, out_file: Path | None = None) -> dict[str, str]:
    if db.scalar(select(Indicator.id).limit(1)) is not None or db.scalar(select(User.id).limit(1)) is not None:
        raise RuntimeError("Database is not empty. Use --reset (SQLite dev only) to rebuild the demo data.")
    org_a = Organisation(name="Demo Bank Kenya (synthetic)", kind="bank", origin=ORIGIN)
    org_b = Organisation(name="Demo Mobile Money Co (synthetic)", kind="telco", origin=ORIGIN)
    db.add_all([org_a, org_b])
    db.flush()
    mod = _user(db, settings, "moderator@demo.example", "moderator", name="Demo Moderator")
    mod2 = _user(db, settings, "moderator2@demo.example", "moderator", name="Demo Moderator Two")
    admin = _user(db, settings, "admin@demo.example", "platform_admin", name="Demo Platform Admin")
    a_admin = _user(db, settings, "orgadmin@bank.demo.example", "org_admin", org_a, "Demo Bank Admin")
    a_analyst = _user(db, settings, "analyst@bank.demo.example", "org_analyst", org_a, "Demo Bank Analyst")
    b_admin = _user(db, settings, "orgadmin@momo.demo.example", "org_admin", org_b, "Demo MoMo Admin")
    reporters = [_user(db, settings, f"reporter{i}@demo.example", "reporter", name=f"Demo Reporter {i}") for i in range(1, 7)]
    db.flush()

    n = {"b": 0}

    def rep(i: int, itype: str, value: str, desc: str, cat: str, who: int | None = None, org: Organisation | None = None, msg: str | None = None,
            county: str = "Nairobi", amount: int | None = None, files: list[bytes] | None = None, days_ago: int = 0, bucket: str | None = None):
        n["b"] += 1
        user = reporters[who] if who is not None else None
        res = submit_report(
            db, settings,
            SubmitInput(itype=itype, value=value, description=desc, category=cat, message_text=msg, county=county, amount_kes=amount, consent_privacy=True, consent_truth=True,
                        consent_share_partners=True, files=files or []),
            reporter=user, bucket=bucket or f"seed-bucket-{who if who is not None else 'anon'}-{n['b']}", owning_org_id=org.id if org else None, origin=ORIGIN,
        )
        res.report.created_at = utcnow() - timedelta(days=days_ago, hours=n["b"] % 7)
        return res.report

    # --- verified via 3 independent reporters ---
    r1 = rep(1, "phone", "0700 000 001", "Called pretending to be a mobile-money agent and asked me to send back a mistaken transfer.", "reversal", 0, amount=2500, days_ago=9, files=[_png("Call log, synthetic")])
    r2 = rep(1, "phone", "+254700000001", "Same number sent me an SMS saying money was sent by mistake and asked me to return it.", "reversal", 1, county="Mombasa", days_ago=7)
    r3 = rep(1, "phone", "254700000001", "Got a call from this number about a reversal, I did not send anything.", "reversal", 2, county="Kisumu", days_ago=5)
    rep(1, "phone", "0700 000 001", "Second report from the same reporter about the same number (does not count as independent).", "reversal", 0, days_ago=4)
    # --- verified via moderator primary evidence ---
    r5 = rep(2, "url", "https://safaricom-bonus.example.test/claim?utm_source=sms", "SMS linked to a fake bonus page asking for my M-Pesa PIN.", "phishing", 3, days_ago=8, files=[_png("Phishing page, synthetic")])
    # --- unverified (2 independent) ---
    r6 = rep(3, "email", "Payments.Team@fake-bank.example", "Email claiming my account is suspended and asking me to confirm details.", "phishing", 1, days_ago=6)
    r7 = rep(3, "email", "payments.team@fake-bank.example", "Received the same account suspension email.", "phishing", 4, days_ago=3)
    # --- single-report unverified ---
    r8 = rep(4, "wallet", "0x00000000000000000000000000000000000dEaD1", "Investment group on social media asked me to send crypto to this address for guaranteed returns.", "investment", 2, days_ago=2, county="Nakuru")
    # --- pending (not public yet) ---
    rep(5, "phone", "0711 000 042", "Caller offered a job and asked for a registration fee by mobile money.", "jobs", 5, days_ago=0)
    # --- awaiting evidence ---
    r10 = rep(6, "social", "@quick.cash.demo", "Social media page promising to double any amount sent in 24 hours.", "investment", 3, days_ago=1)
    # --- messages (similarity) ---
    m1 = rep(7, "message", "", "Message claiming I won a prize and must pay a processing fee.", "prize", 0, msg="Congratulations! You have won KES 250,000 in the Demo Lottery. Pay a processing fee of KES 500 to the till number 000000 to claim today. Reply urgently.", days_ago=6)
    m2 = rep(7, "message", "", "Same prize message received.", "prize", 1, msg="CONGRATULATIONS you have won KES 300,000 in the Demo Lottery! Pay processing fee KES 700 to till 000000 to claim today. Reply urgently!", days_ago=4)
    # --- org-owned reports ---
    o1 = rep(8, "url", "http://secure-login.demo-bank.invalid/verify", "Customer reported a look-alike login page for our bank.", "phishing", None, org=org_a, bucket="org-a", days_ago=3, files=[_png("Org A evidence, synthetic")], county="Nairobi")
    o2 = rep(9, "phone", "0700 000 077", "Customers reported calls asking for OTP codes.", "impersonation", None, org=org_b, bucket="org-b", days_ago=2, county="Nairobi")
    o3 = rep(10, "email", "alerts@momo-support.example", "Phishing email using our brand.", "phishing", None, org=org_b, bucket="org-b-2", days_ago=1, county="Mombasa")
    db.flush()

    # moderation through the real workflow
    decide(db, settings, mod, r1.id, "accept", "Consistent with other reports on this number.")
    decide(db, settings, mod, r2.id, "accept", "Independent reporter, same pattern.")
    decide(db, settings, mod, r3.id, "verify", "Three independent reporters describe the same reversal story.")
    decide(db, settings, mod, r5.id, "attach_evidence", "Captured the live page; matches SMS text.", file_bytes=_png("Moderator capture, synthetic"))
    decide(db, settings, mod, r5.id, "verify", "Moderator captured primary evidence of the credential page.")
    decide(db, settings, mod, r6.id, "accept", "Plausible phishing report.")
    decide(db, settings, mod, r7.id, "accept", "Second independent report.")
    decide(db, settings, mod, r8.id, "accept", "Accepted as reported, needs more evidence to verify.")
    decide(db, settings, mod, r10.id, "request_evidence", "Please add a screenshot of the page and the date you saw it.")
    decide(db, settings, mod, m1.id, "accept", "Typical advance-fee prize message.")
    decide(db, settings, mod2, m2.id, "accept", "Near-duplicate of the first prize message.")
    decide(db, settings, mod, o1.id, "accept", "Institution-submitted, reviewed.")
    decide(db, settings, mod, o2.id, "accept", "Institution-submitted, reviewed.")
    decide(db, settings, mod, o3.id, "accept", "Institution-submitted, reviewed.")

    # an open correction on an unverified record
    ind6 = db.get(Indicator, r6.indicator_id)
    assert ind6 is not None
    submit_correction(db, settings, ind6.id, "owner", "This is a legitimate support mailbox used by a regional office, please review.", "owner@contact.demo.example", True)

    # org cases, notes, alerts
    scope = TenantScope(db, org_a.id)
    case = scope.create_case("Investigate prize-message campaign (synthetic)", a_analyst.id)
    scope.link_indicator(case, db.get(Indicator, m1.indicator_id).id)  # type: ignore[union-attr]
    scope.add_note(case.id, a_analyst.id, "Synthetic note: compare with customer complaints from last week.")
    db.add(AlertSubscription(user_id=a_analyst.id, org_id=org_a.id, category="phishing", frequency="instant"))
    db.add(AlertSubscription(user_id=reporters[0].id, category="reversal", frequency="instant"))
    db.add(AlertSubscription(user_id=reporters[2].id, category="prize", frequency="daily"))
    key, full = orgs.create_key(scope, a_admin, "Demo integration (test)", ["lookup", "report", "intel", "analytics"], "test", settings)
    notify.run_digest(db)
    db.flush()

    creds = {
        "password (all demo accounts)": DEMO_PASSWORD,
        "moderator": "moderator@demo.example",
        "platform_admin": "admin@demo.example",
        "org_admin_A": "orgadmin@bank.demo.example",
        "org_analyst_A": "analyst@bank.demo.example",
        "org_admin_B": "orgadmin@momo.demo.example",
        "reporter": "reporter1@demo.example",
        "demo_api_key_org_A": full,
    }
    from .accounts import current_secret

    for u in (mod, mod2, admin, a_admin, a_analyst, b_admin):
        creds[f"totp:{u.email}"] = current_secret(settings, u) or ""
    _ = (key, Case)
    if out_file:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text("SYNTHETIC DEMO CREDENTIALS. Local use only. Never reuse.\n" + "\n".join(f"{k}: {v}" for k, v in creds.items()) + "\n")
        out_file.chmod(0o600)
    return creds
