import pytest

from scamshield import similarity as sim
from scamshield.analysis import AnalysisContext, Prior, analyse_message
from scamshield.llm_adapter import ExternalLLMAdapter, LLMNotConfigured, NullLLMAdapter


def test_shingles_and_jaccard():
    assert sim.shingles("") == set()
    assert sim.shingles("one two") == {"one two"}
    a, b = sim.shingles("send money now to claim your prize today"), sim.shingles("send money now to claim your prize tomorrow")
    assert 0 < sim.jaccard(a, b) < 1
    assert sim.jaccard(set(), set()) == 0.0


def test_minhash_similarity_ranks_near_duplicates_high():
    base = "Congratulations you have won KES 250000 in the lottery pay a processing fee to till 123456 to claim today"
    near = "CONGRATULATIONS you have won KES 300000 in the lottery! Pay processing fee to till 654321 to claim today"
    far = "Meeting moved to 10am tomorrow please update the tracker before the call and bring the report"
    s = sim.minhash(base)
    assert len(s) == sim.NUM_PERM
    assert sim.estimate_similarity(s, sim.minhash(near)) > 0.6
    assert sim.estimate_similarity(s, sim.minhash(far)) < 0.2
    assert sim.estimate_similarity(s, s) == 1.0
    assert sim.minhash("") == []
    assert sim.estimate_similarity([], s) == 0.0
    assert sim.estimate_similarity([1], [1, 2]) == 0.0


def test_most_similar_sorting_and_threshold():
    s = sim.minhash("alpha beta gamma delta epsilon zeta eta theta")
    c1 = (1, sim.minhash("alpha beta gamma delta epsilon zeta eta theta"))
    c2 = (2, sim.minhash("alpha beta gamma delta epsilon zeta iota kappa"))
    c3 = (3, sim.minhash("completely different words appear in this unrelated sentence"))
    out = sim.most_similar(s, [c3, c2, c1], threshold=0.2)
    assert [i for i, _ in out][:2] == [1, 2] and all(i != 3 for i, _ in out)


def test_scam_message_flagged_with_reasons_and_highlights():
    r = analyse_message("URGENT: Your KCB account will be suspended. Confirm your PIN at http://kcb-login.top now or face legal action.")
    assert r.label == "several_warning_signs"
    kinds = {x["signal"] for x in r.reasons}
    assert {"urgency", "credential_request", "threat", "suspicious_url", "organisation_named", "impersonation_pattern"} <= kinds
    assert r.highlights and all(h["end"] > h["start"] for h in r.highlights)
    assert 0.4 < r.confidence <= 0.95
    assert "not proof" in r.disclaimer
    d = r.as_dict()
    assert set(d) >= {"label", "confidence", "reasons", "matched_prior_reports"}


def test_benign_message_few_signs_and_low_confidence():
    r = analyse_message("Hi, are we still meeting for lunch tomorrow?")
    assert r.label == "few_warning_signs" and r.confidence < 0.5
    assert any(x["signal"] == "none" for x in r.reasons)


def test_safety_warning_is_not_a_credential_request():
    r = analyse_message("Your code is 123456. Do not share your PIN or code with anyone.")
    assert all(x["signal"] != "credential_request" for x in r.reasons)


@pytest.mark.parametrize("url,fragment", [
    ("http://bit.ly/x", "shortener"), ("http://192.0.2.5/login", "IP address"), ("http://xn--bcher-kva.example/", "look-alike"),
    ("http://safaricom-login.example/", "official domain"), ("http://pay.thing.top/x", "throw-away"), ("http://a.b.c.d.e.example/", "sub-domains"),
])
def test_url_findings(url, fragment):
    r = analyse_message(f"Please visit {url} to continue")
    assert any(fragment in x["text"] for x in r.reasons if x["signal"] == "suspicious_url")


def test_official_domain_not_flagged():
    r = analyse_message("Safaricom offers at https://www.safaricom.co.ke today")
    assert all(x["signal"] != "suspicious_url" for x in r.reasons)


def test_prior_reports_raise_score_and_are_listed():
    prior_v = Prior(7, "phone", "+2547•• ••• 001", "verified", 3, "exact")
    prior_s = Prior(9, "message", "Message pattern", "unverified", 1, "similar", 0.8)
    ctx = AnalysisContext(lookup_indicator=lambda t, v: prior_v if t == "phone" else None, similar_messages=lambda text: [prior_s])
    plain = analyse_message("Call me on 0700000001")
    boosted = analyse_message("Call me on 0700000001", ctx)
    assert boosted.score > plain.score
    assert len(boosted.matched_prior_reports) == 2
    assert any("similar" in x["text"] or "matches" in x["text"] for x in boosted.reasons)
    assert boosted.confidence > plain.confidence


def test_llm_adapter_off_by_default_and_placeholder_raises():
    class Fake:
        name = "fake"

        def analyse(self, text):
            return {"reasons": ["Model noticed a pattern."], "model": "fake-1"}

    base = analyse_message("hello there friend", llm=Fake(), llm_enabled=False)
    assert not base.model_assisted
    on = analyse_message("hello there friend", llm=Fake(), llm_enabled=True)
    assert on.model_assisted and on.engine.endswith("+fake-1") and on.label == base.label
    none = analyse_message("hello there friend", llm=NullLLMAdapter(), llm_enabled=True)
    assert not none.model_assisted
    with pytest.raises(LLMNotConfigured):
        ExternalLLMAdapter().analyse("x")
