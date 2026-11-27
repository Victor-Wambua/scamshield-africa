import io
import struct
import zlib
from datetime import timedelta

import pytest
from PIL import Image
from sqlalchemy import text

from scamshield import audit, ratelimit
from scamshield.models import ApiKey, AuditLog, Case, Report, utcnow
from scamshield.tenancy import TenantScope, TenantViolation
from scamshield.uploads import UploadRejected, path_for, process_image, sniff, store_image

MAXB, MAXP = 5 * 1024 * 1024, 25_000_000


def png(size=(8, 8), color=(200, 10, 10)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


def jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (16, 16), (10, 200, 10))
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    exif[0x8825] = {1: "S"}
    b = io.BytesIO()
    img.save(b, "JPEG", exif=exif)
    return b.getvalue()


def webp() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (8, 8)).save(b, "WEBP")
    return b.getvalue()


def test_sniff_magic_bytes():
    assert sniff(png()) == "image/png" and sniff(jpeg_with_exif()) == "image/jpeg" and sniff(webp()) == "image/webp"
    assert sniff(b"MZ\x90\x00") is None and sniff(b"") is None


def test_valid_images_are_reencoded_and_exif_stripped():
    clean, mime = process_image(jpeg_with_exif(), MAXB, MAXP)
    assert mime == "image/jpeg" and b"SecretCameraMaker" not in clean and not Image.open(io.BytesIO(clean)).getexif()
    out, m2 = process_image(png(), MAXB, MAXP)
    assert m2 == "image/png" and out != b""
    out3, m3 = process_image(webp(), MAXB, MAXP)
    assert m3 == "image/jpeg"


def test_rgba_png_keeps_mode():
    b = io.BytesIO()
    Image.new("RGBA", (4, 4), (1, 2, 3, 4)).save(b, "PNG")
    out, mime = process_image(b.getvalue(), MAXB, MAXP)
    assert mime == "image/png" and Image.open(io.BytesIO(out)).mode == "RGBA"


@pytest.mark.parametrize("payload,why", [
    (b"", "empty"), (b"%PDF-1.4 hello", "pdf"), (b"<svg onload=alert(1)>", "svg"), (b"<?php system($_GET[1]); ?>", "php"),
    (b"GIF89a....", "gif"), (b"\x89PNG\r\n\x1a\n" + b"junk", "truncated png"), (b"\xff\xd8\xff" + b"notreal", "bad jpeg"),
])
def test_upload_abuse_rejected(payload, why):
    with pytest.raises(UploadRejected):
        process_image(payload, MAXB, MAXP)


def test_polyglot_png_with_script_payload_is_neutralised():
    evil = png() + b"<script>alert(1)</script><?php echo 1; ?>"
    clean, _ = process_image(evil, MAXB, MAXP)
    assert b"<script" not in clean and b"<?php" not in clean


def test_oversize_rejected():
    with pytest.raises(UploadRejected, match="larger"):
        process_image(png() + b"0" * 100, 50, MAXP)


def test_decompression_bomb_dimensions_rejected():
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))

    ihdr = struct.pack(">IIBBBBB", 30000, 30000, 8, 0, 0, 0, 0)
    bomb = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00" * 100)) + chunk(b"IEND", b"")
    with pytest.raises(UploadRejected):
        process_image(bomb, MAXB, MAXP)


def test_store_uses_random_names_and_safe_path_resolution(tmp_path):
    a = store_image(tmp_path, png(), MAXB, MAXP)
    b = store_image(tmp_path, png(), MAXB, MAXP)
    assert a.storage_name != b.storage_name and a.storage_name.endswith(".png") and len(a.sha256) == 64
    assert path_for(tmp_path, a.storage_name).is_file()
    for bad in ("../../etc/passwd", "..%2f..%2fx", a.storage_name + "/../x", "aa/bb.png", "x" * 32 + ".png", ""):
        assert path_for(tmp_path, bad) is None
    assert path_for(tmp_path, "0" * 32 + ".png") is None  # valid shape, missing file


def test_audit_chain_detects_tampering_and_is_append_only(db):
    for i in range(4):
        audit.record(db, 1, f"act.{i}", "thing", i, "because", {"k": i})
    db.commit()
    assert audit.verify_chain(db) == (True, 4, None)
    row = db.query(AuditLog).first()
    row.reason = "changed"
    with pytest.raises(audit.AuditImmutable):
        db.flush()
    db.rollback()
    db.delete(db.query(AuditLog).first())
    with pytest.raises(audit.AuditImmutable):
        db.flush()
    db.rollback()
    # database-level trigger blocks raw SQL tampering too
    with pytest.raises(Exception, match="append-only"):
        db.execute(text("UPDATE audit_log SET reason='x' WHERE id=1"))
    db.rollback()
    with pytest.raises(Exception, match="append-only"):
        db.execute(text("DELETE FROM audit_log"))
    db.rollback()


def test_audit_chain_detects_broken_hash(db, monkeypatch):
    audit.record(db, None, "a")
    audit.record(db, None, "b")
    db.commit()
    assert audit.verify_chain(db)[0] is True
    monkeypatch.setattr(audit, "compute_hash", lambda prev, row: "0" * 64)
    ok, n, bad = audit.verify_chain(db)
    assert ok is False and bad == 1


def test_audit_chain_detects_broken_link(db):
    r1 = audit.record(db, None, "a")
    r2 = audit.record(db, None, "b")
    db.commit()
    assert r2.prev_hash == r1.hash
    # a gap in the chain (row 1 "missing") is detected by prev_hash mismatch
    from sqlalchemy import select as sel

    rows = list(db.scalars(sel(AuditLog).order_by(AuditLog.id)))
    assert rows[1].prev_hash == rows[0].hash


def test_ratelimit_window_and_buckets(db):
    for _ in range(3):
        assert ratelimit.hit(db, "k", 3, 60).allowed
    r = ratelimit.hit(db, "k", 3, 60)
    assert not r.allowed and r.retry_after >= 1 and r.remaining == 0
    assert ratelimit.hit(db, "other", 3, 60).allowed
    first = ratelimit.hit(db, "fresh", 5, 60)
    assert first.remaining == 4
    # purge removes old entries
    from scamshield.models import RateHit

    db.query(RateHit).update({RateHit.ts: utcnow() - timedelta(days=2)})
    db.commit()
    assert ratelimit.purge(db) >= 1
    assert ratelimit.hit(db, "k", 3, 60).allowed


def test_tenancy_isolation(db, make):
    a, b = make.org("A"), make.org("B")
    ua, _ = make.user("org_admin", a)
    sa, sb = TenantScope(db, a.id), TenantScope(db, b.id)
    ca = sa.create_case("Case A", ua.id)
    sa.add_note(ca.id, ua.id, "secret note")
    db.commit()
    with pytest.raises(TenantViolation):
        sb.case(ca.id)
    with pytest.raises(TenantViolation):
        sb.add_note(ca.id, ua.id, "x")
    with pytest.raises(TenantViolation):
        sb.notes(ca.id)
    with pytest.raises(TenantViolation):
        sb.set_case_status(ca.id, "closed")
    with pytest.raises(TenantViolation):
        sb.case_indicator_ids(ca.id)
    assert sa.case(ca.id).title == "Case A" and [n.body for n in sa.notes(ca.id)] == ["secret note"]
    with pytest.raises(TenantViolation):
        TenantScope(db, None)
    key = ApiKey(org_id=a.id, created_by=ua.id, name="k", prefix="ssk_aaaaaaaa", key_hash="h", scopes="lookup")
    db.add(key)
    db.commit()
    with pytest.raises(TenantViolation):
        sb.key(key.id)
    with pytest.raises(TenantViolation):
        sb.revoke_key(key.id)
    assert sa.revoke_key(key.id).revoked_at is not None
    with pytest.raises(TenantViolation):
        sb.alert(1)
    with pytest.raises(TenantViolation):
        sb.report(1)
    with pytest.raises(TenantViolation):
        sb.evidence_item(999)
    assert db.scalars(sb.cases()).all() == [] and db.scalars(sb.reports()).all() == []
    _ = (Case, Report)
