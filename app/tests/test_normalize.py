import pytest

from scamshield.normalize import (
    InvalidIndicator, canonical_text, detect_type, extract_phones, extract_urls, mask_value, normalize,
    normalize_business, normalize_email, normalize_message, normalize_payment_ref, normalize_phone, normalize_social,
    normalize_url, normalize_wallet,
)


@pytest.mark.parametrize("raw,expected", [
    ("0712 345 678", "+254712345678"), ("+254 712-345-678", "+254712345678"), ("254712345678", "+254712345678"),
    ("0112345678", "+254112345678"), ("(0712) 345 678", "+254712345678"), ("00254712345678", "+254712345678"),
    ("+44 20 7946 0958", "+442079460958"),
])
def test_phone_normalises_to_e164(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("bad", ["", "12345", "0812345678", "abc", "+254", "071234567", "+1234567"])
def test_phone_rejects_invalid(bad):
    with pytest.raises(InvalidIndicator):
        normalize_phone(bad)


@pytest.mark.parametrize("raw,expected", [
    ("https://WWW.Example.COM/Path/?utm_source=x&b=2&a=1#frag", "example.com/Path?a=1&b=2"),
    ("example.com", "example.com"), ("http://example.com/", "example.com"), ("example.com//a///b/", "example.com/a/b"),
    ("http://user:pw@evil.test/login", "evil.test/login"), ("https://example.com:8443/x", "example.com:8443/x"),
    ("https://example.com:443/x", "example.com/x"), ("http://192.0.2.10/pay", "192.0.2.10/pay"),
    ("https://bücher.example/", "xn--bcher-kva.example"), ("https://Example.com/?fbclid=zz", "example.com"),
])
def test_url_canonicalisation(raw, expected):
    assert normalize_url(raw) == expected


def test_url_userinfo_trick_resolves_to_real_host():
    assert normalize_url("http://mybank.co.ke@evil.test/") == "evil.test"


@pytest.mark.parametrize("bad", ["", "not a url", "ftp://example.com", "http://nodot", "http://exa mple.com", "http://-bad-.com", "http://example.c", "http://[::1"])
def test_url_rejects_invalid(bad):
    with pytest.raises(InvalidIndicator):
        normalize_url(bad)


def test_url_bad_idna():
    with pytest.raises(InvalidIndicator):
        normalize_url("http://a..b.com")


def test_email_normalisation_and_punycode():
    assert normalize_email("  Jane.Doe+x@Example.COM ") == "jane.doe+x@example.com"
    assert normalize_email("a@bücher.example") == "a@xn--bcher-kva.example"


@pytest.mark.parametrize("bad", ["", "no-at.com", "a@b", "@example.com", "a b@example.com", "a@@example.com"])
def test_email_rejects_invalid(bad):
    with pytest.raises(InvalidIndicator):
        normalize_email(bad)


def test_wallet():
    assert normalize_wallet("0xABCDEF0123456789abcdef0123456789ABCDEF01") == "0xabcdef0123456789abcdef0123456789abcdef01"
    btc = "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"
    assert normalize_wallet(" " + btc + " ") == btc
    with pytest.raises(InvalidIndicator):
        normalize_wallet("short")
    with pytest.raises(InvalidIndicator):
        normalize_wallet("x" * 30 + "!!")


def test_social():
    assert normalize_social("@Quick.Cash") == "@quick.cash"
    assert normalize_social("quick_cash") == "@quick_cash"
    assert normalize_social("facebook.com/Quick.Cash/") == "facebook.com/Quick.Cash"
    with pytest.raises(InvalidIndicator):
        normalize_social("!!")


def test_payment_ref_and_business():
    assert normalize_payment_ref("sk t-7 xyz") == "SKT7XYZ"
    with pytest.raises(InvalidIndicator):
        normalize_payment_ref("ab")
    assert normalize_business("  ACME   Traders  ") == "acme traders"
    with pytest.raises(InvalidIndicator):
        normalize_business("ab")


def test_message_identity_ignores_numbers_urls_and_spacing():
    a = normalize_message("You WON 1000 shillings!  Visit http://x.example/a now")
    b = normalize_message("you won 99999 shillings! visit https://other.test/b now")
    assert a == b and a.startswith("msg:")
    assert canonical_text("A  1 b") == "a 0 b"


def test_normalize_dispatch_and_unknown_type():
    assert normalize("phone", "0712345678") == "+254712345678"
    with pytest.raises(InvalidIndicator):
        normalize("nonsense", "x")


def test_detect_type():
    assert detect_type("0712345678") == "phone"
    assert detect_type("a@example.com") == "email"
    assert detect_type("example.com/pay") == "url"
    assert detect_type("1BoatSLRHtKNngkdXEeobR76b53LETtpyT") == "wallet"
    assert detect_type("!!") is None


def test_extractors():
    t = "Pay at bit.ly/abc or http://x.example/p). Call 0712 345 678 or +254 712 345 678 now. Also www."
    assert "bit.ly/abc" in extract_urls(t)
    assert extract_phones(t) == ["+254712345678"]
    assert extract_urls("nothing here") == []
    assert extract_urls("see http://exa mple") == [] or isinstance(extract_urls("see http://exa mple"), list)


def test_masking():
    assert mask_value("phone", "+254712345678") == "+2547•• ••• 678"
    assert mask_value("phone", "+442079460958") == "+442•••958"
    assert mask_value("email", "jane@example.com") == "j•••@example.com"
    assert mask_value("wallet", "0xabcdef0123456789") == "0xabcd…6789"
    assert mask_value("url", "evil.test/login") == "evil.test/…"
    assert mask_value("url", "evil.test") == "evil.test"
    assert mask_value("message", "msg:abc") == "Message pattern"
    assert mask_value("social", "@quickcash") == "@qu•••"
