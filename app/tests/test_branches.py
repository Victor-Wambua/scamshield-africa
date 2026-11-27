"""Edge-case and defensive-branch tests for the critical business-rule modules."""

import io
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from helpers import png_bytes, submit
from scamshield import cli, moderation, uploads
from scamshield.config import set_settings
from scamshield.corrections import decide_correction, submit_correction
from scamshield.models import Indicator, Report, User
from scamshield.moderation import ModerationError, decide
from scamshield.normalize import extract_phones, extract_urls, normalize_social
from scamshield.permissions import PERMISSIONS
from scamshield.reports import analysis_context, public_view

GOOD = dict(relationship="owner", explanation="This number belongs to my shop and is not a scam number.", contact_email="o@example.com", acknowledged=True)


def test_mark_unverified_on_removed_indicator_refused(db, settings, make):
    mod, _ = make.user("moderator")
    admin, _ = make.user("platform_admin")
    settings.verify_min_independent = 1
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "verify", "verified before removal test")
    ind = db.get(Indicator, r.indicator_id)
    c = submit_correction(db, settings, ind.id, **GOOD)
    decide_correction(db, settings, admin, c.id, "remove", "legal takedown for branch test")
    db.commit()
    with pytest.raises(ModerationError, match="removed"):
        decide(db, settings, mod, r.id, "mark_unverified", "attempt to resurrect record")
    with pytest.raises(ModerationError, match="removed"):
        decide(db, settings, mod, r.id, "verify", "attempt to verify removed record")


def test_verifying_already_verified_indicator_does_not_realert(db, settings, make):
    from scamshield.models import AlertSubscription, Notification

    settings.verify_min_independent = 1
    mod, _ = make.user("moderator")
    sub, _ = make.user()
    db.add(AlertSubscription(user_id=sub.id, category="reversal"))
    db.commit()
    a = submit(db, settings, bucket="a1").report
    b = submit(db, settings, bucket="a2").report
    decide(db, settings, mod, a.id, "verify", "first verification of the record")
    decide(db, settings, mod, b.id, "verify", "second report verified too")
    assert len(db.scalars(select(Notification).where(Notification.user_id == sub.id, Notification.kind == "new_verified")).all()) == 1


def test_merge_moves_evidence_to_target(db, settings, make):
    from scamshield.models import Evidence

    mod, _ = make.user("moderator")
    a = submit(db, settings, "one-scam.test", "url", bucket="e1").report
    b = submit(db, settings, "two-scam.test", "url", bucket="e2", files=[png_bytes()]).report
    decide(db, settings, mod, b.id, "merge", "same campaign, evidence moves", target_indicator_id=a.indicator_id)
    assert db.scalar(select(Evidence)).indicator_id == a.indicator_id


def test_restrict_requires_permission_even_if_decide_allowed(db, settings, make, monkeypatch):
    mod, _ = make.user("moderator")
    u, _ = make.user()
    r = submit(db, settings, reporter=u).report
    monkeypatch.setitem(PERMISSIONS, "moderator", PERMISSIONS["moderator"] - {"restrict.reporter"})
    with pytest.raises(ModerationError, match="cannot restrict"):
        decide(db, settings, mod, r.id, "restrict_reporter", "no permission to restrict")
    assert not db.get(User, u.id).restricted


def test_upload_dimension_limit_and_path_second_layer(tmp_path, monkeypatch):
    with pytest.raises(uploads.UploadRejected, match="dimensions"):
        uploads.process_image(png_bytes(), 5 * 1024 * 1024, 100)  # 12x12 = 144 px is over the cap but under 2x (Pillow bomb guard)
    stored = uploads.store_image(tmp_path, png_bytes(), 5 * 1024 * 1024, 25_000_000)
    monkeypatch.setattr(uploads, "_NAME_RE", __import__("re").compile(r"^.*$"))
    assert uploads.path_for(tmp_path, "../../etc/passwd") is None
    assert uploads.path_for(tmp_path, stored.storage_name) is not None


def test_normalizer_fallbacks():
    assert normalize_social("abc.d") == "@abc.d"
    assert extract_urls("a " + "a" * 70 + ".com b") == []
    assert extract_urls("see example.com/x and again example.com/x") == ["example.com/x"]
    assert extract_phones("call 0712345678 or 0712 345 678") == ["+254712345678"]


def test_analysis_context_lookup_and_public_message_value(db, settings, make):
    mod, _ = make.user("moderator")
    ctx = analysis_context(db)
    assert ctx.lookup_indicator("url", "nope.test") is None
    r = submit(db, settings, "", "message", message_text="Win a prize now, pay a processing fee to till 123456 today friend", category="prize").report
    decide(db, settings, mod, r.id, "accept", "accepted message pattern")
    db.commit()
    ind = db.get(Indicator, r.indicator_id)
    assert public_view(ind, exact=True)["value"].startswith("Message pattern")
    got = analysis_context(db).lookup_indicator("phone", "+254700000001")
    assert got is None
    r2 = submit(db, settings).report
    decide(db, settings, mod, r2.id, "accept", "accepted for lookup test")
    db.commit()
    assert analysis_context(db).lookup_indicator("phone", "+254700000001").status == "unverified"
    assert analysis_context(db).similar_messages("Win a prize now, pay a processing fee to till 999999 today friend")


def test_similar_messages_collapse_per_indicator(db, settings, make):
    from scamshield.reports import message_priors

    mod, _ = make.user("moderator")
    text = "Congratulations you have won a lottery pay a processing fee to till 123456 to claim today please"
    for i in range(2):
        r = submit(db, settings, "", "message", message_text=text, category="prize", bucket=f"s{i}").report
        decide(db, settings, mod, r.id, "accept", "accepted duplicate message")
    assert len(message_priors(db, text)) == 1


def test_seed_in_process_and_cli_commands(db, settings, tmp_path, monkeypatch, capsys):
    from scamshield.seed import DEMO_PASSWORD, seed

    creds = seed(db, settings, tmp_path / "creds.txt")
    db.commit()
    assert creds["password (all demo accounts)"] == DEMO_PASSWORD and (tmp_path / "creds.txt").exists()
    with pytest.raises(RuntimeError, match="not empty"):
        seed(db, settings)
    monkeypatch.chdir(tmp_path)
    set_settings(settings)
    assert cli.main(["audit-verify"]) == 0 and "audit chain OK" in capsys.readouterr().out
    assert cli.main(["digest"]) == 0
    monkeypatch.setenv("SS_NEW_PASSWORD", "Cli-Pass-1234567")
    assert cli.main(["create-user", "clinew@example.com", "reporter"]) == 0
    assert cli.main(["seed", "--reset"]) == 0
    assert (tmp_path / "data" / "demo-credentials.txt").exists()
    settings.database_url = "postgresql://x/y"
    assert cli.main(["seed", "--reset"]) == 2
    assert cli.main(["evaluate"]) == 0


def test_cli_audit_verify_reports_broken_chain(db, settings, tmp_path, monkeypatch, capsys):
    from scamshield import audit

    audit.record(db, None, "a")
    audit.record(db, None, "b")
    db.commit()
    monkeypatch.setattr(audit, "compute_hash", lambda prev, row: "bad")
    monkeypatch.chdir(tmp_path)
    set_settings(settings)
    assert cli.main(["audit-verify"]) == 1
    assert "BROKEN" in capsys.readouterr().out
    _ = (Path, io, Image, Report)
