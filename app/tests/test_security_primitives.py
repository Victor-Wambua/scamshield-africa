import pyotp
import pytest

from scamshield import security as sec


def test_password_hash_is_argon2id_with_production_parameters():
    from argon2 import PasswordHasher

    prod = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
    h = prod.hash("Example-Pass-1")
    assert h.startswith("$argon2id$") and "m=19456" in h
    assert sec.verify_password(sec._ph.hash("pw-Example-1"), "pw-Example-1")


def test_verify_password_handles_wrong_and_garbage():
    h = sec.hash_password("Right-Pass-123")
    assert sec.verify_password(h, "Right-Pass-123")
    assert not sec.verify_password(h, "wrong")
    assert not sec.verify_password("not-a-hash", "x")


@pytest.mark.parametrize("pw,ok", [("short1", False), ("longenoughbutnodigits", False), ("1234567890123", False), ("Valid-Pass-12", True), ("password123", False), ("x" * 201 + "1", False)])
def test_password_policy(pw, ok):
    assert (sec.password_problems(pw) == []) is ok


def test_field_encryption_roundtrip_and_wrong_key():
    t = sec.encrypt_field("k1", "JBSWY3DPEHPK3PXP")
    assert "JBSWY" not in t and sec.decrypt_field("k1", t) == "JBSWY3DPEHPK3PXP"
    assert sec.decrypt_field("other", t) is None


def test_totp_verify_window_and_format():
    s = sec.new_totp_secret()
    code = pyotp.TOTP(s).now()
    assert sec.verify_totp(s, code) and sec.verify_totp(s, code[:3] + " " + code[3:])
    assert not sec.verify_totp(s, "000000" if code != "000000" else "111111")
    assert not sec.verify_totp(s, "abc") and not sec.verify_totp(s, "")
    assert "otpauth://totp/" in sec.totp_uri(s, "a@example.com")


def test_recovery_codes():
    codes = sec.new_recovery_codes()
    assert len(codes) == 8 and len(set(codes)) == 8
    assert sec.hash_recovery_code(codes[0]) == sec.hash_recovery_code(codes[0].upper())


def test_csrf_binding():
    t = sec.csrf_for("s", "sess1")
    assert sec.csrf_valid("s", "sess1", t)
    assert not sec.csrf_valid("s", "sess2", t)
    assert not sec.csrf_valid("other", "sess1", t)
    assert not sec.csrf_valid("s", "sess1", None) and not sec.csrf_valid("s", "", t) and not sec.csrf_valid("s", "sess1", "bad")


def test_session_token_ids_are_hashed():
    tok = sec.new_token()
    assert sec.token_id(tok) != tok and len(sec.token_id(tok)) == 64


def test_device_bucket_is_salted_and_coarse():
    a = sec.device_bucket("s", "203.0.113.5", "UA")
    assert a == sec.device_bucket("s", "203.0.113.200", "UA")  # same /24
    assert a != sec.device_bucket("s", "203.0.114.5", "UA")
    assert a != sec.device_bucket("t", "203.0.113.5", "UA")
    assert "203" not in a
    assert sec.device_bucket("s", "2001:db8:1:2::1", "UA")


def test_api_key_generation_and_matching():
    full, prefix, h = sec.generate_api_key()
    assert full.startswith(prefix + "_") and sec.split_api_key(full) == prefix
    assert sec.api_key_matches(full, h) and not sec.api_key_matches(full + "x", h)
    assert full not in h
    assert sec.split_api_key("garbage") is None and sec.split_api_key("") is None
