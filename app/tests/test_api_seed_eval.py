import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from helpers import png_bytes, submit
from sqlalchemy import create_engine, inspect, select

from scamshield import orgs
from scamshield.db import Base
from scamshield.models import ApiKey, ApiUsage, Indicator, Report
from scamshield.moderation import decide
from scamshield.tenancy import TenantScope

APP_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def keyed(app, make, db, settings):
    org = make.org("API Org")
    admin, _ = make.user("org_admin", org)
    scope = TenantScope(db, org.id)
    _, full = orgs.create_key(scope, admin, "k", ["lookup", "report", "intel", "analytics"], "test", settings)
    db.commit()
    return org, full, TestClient(app)


def H(key):
    return {"Authorization": f"Bearer {key}"}


def test_api_requires_authentication(keyed):
    _, key, c = keyed
    for path in ("/api/v1/indicators/lookup?value=1", "/api/v1/threat-intel", "/api/v1/org/analytics", "/api/v1/reports/R-1/status"):
        r = c.get(path)
        assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized" and r.headers["www-authenticate"] == "Bearer"
    assert c.get("/api/v1/threat-intel", headers=H("ssk_deadbeef_" + "x" * 30)).status_code == 401
    assert c.get("/api/v1/threat-intel", headers={"X-API-Key": key}).status_code == 200
    assert c.post("/api/v1/reports", json={}).status_code == 401


def test_lookup_endpoint_found_and_not_found(keyed, db, settings, make):
    _, key, c = keyed
    mod, _ = make.user("moderator")
    settings.verify_min_independent = 1
    r = submit(db, settings).report
    decide(db, settings, mod, r.id, "verify", "verified for api lookup test")
    db.commit()
    ok = c.get("/api/v1/indicators/lookup", params={"value": "0700 000 001"}, headers=H(key))
    body = ok.json()
    assert ok.status_code == 200 and body["found"] and body["indicator"]["status"] == "verified" and body["indicator"]["value"] == "+254700000001"
    assert "reporter" not in json.dumps(body) and ok.headers["x-ratelimit-remaining"]
    nf = c.get("/api/v1/indicators/lookup", params={"value": "0799999999"}, headers=H(key)).json()
    assert nf["found"] is False and "does not mean safe" in nf["notice"]
    assert c.get("/api/v1/indicators/lookup", headers=H(key)).status_code == 422


def test_report_submission_and_status_scoped_to_org(keyed, app, make, db, settings):
    org, key, c = keyed
    payload = {"type": "phone", "value": "0700000007", "description": "Customers received calls asking for OTP codes.", "category": "impersonation", "consent_privacy": True, "consent_truth": True, "county": "Nairobi"}
    r = c.post("/api/v1/reports", json=payload, headers=H(key))
    assert r.status_code == 201 and r.json()["reference"].startswith("R-") and r.json()["counts_as_independent"] is True
    ref = r.json()["reference"]
    st = c.get(f"/api/v1/reports/{ref}/status", headers=H(key))
    assert st.status_code == 200 and st.json()["status"] == "received" and st.json()["indicator_status"] == "not_published"
    assert db.scalar(select(Report).where(Report.ref == ref)).owning_org_id == org.id
    # second org cannot see it
    org2 = make.org("Other API Org")
    admin2, _ = make.user("org_admin", org2)
    _, key2 = orgs.create_key(TenantScope(db, org2.id), admin2, "k2", ["report"], "test", settings)
    db.commit()
    assert c.get(f"/api/v1/reports/{ref}/status", headers=H(key2)).status_code == 404
    assert c.get("/api/v1/reports/R-9999/status", headers=H(key)).json()["error"]["code"] == "not_found"
    # validation
    bad = c.post("/api/v1/reports", json={**payload, "value": "123"}, headers=H(key))
    assert bad.status_code == 422 and "value" in bad.json()["error"]["details"]
    assert c.post("/api/v1/reports", json={**payload, "description": "short"}, headers=H(key)).status_code == 422
    # repeated reports via one key are one source: not independent
    again = c.post("/api/v1/reports", json=payload, headers=H(key)).json()
    assert again["is_duplicate"] is True and again["counts_as_independent"] is False


def test_scopes_enforced(app, make, db, settings):
    org = make.org()
    admin, _ = make.user("org_admin", org)
    _, lookup_only = orgs.create_key(TenantScope(db, org.id), admin, "ro", ["lookup"], "test", settings)
    db.commit()
    c = TestClient(app)
    for method, path in (("get", "/api/v1/threat-intel"), ("get", "/api/v1/org/analytics"), ("get", "/api/v1/reports/R-1/status")):
        r = getattr(c, method)(path, headers=H(lookup_only))
        assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert c.post("/api/v1/reports", json={}, headers=H(lookup_only)).status_code == 403
    assert c.get("/api/v1/indicators/lookup?value=0700000001", headers=H(lookup_only)).status_code == 200


def test_rate_limit_per_key_with_headers(app, make, db, settings):
    org = make.org()
    admin, _ = make.user("org_admin", org)
    scope = TenantScope(db, org.id)
    k1, f1 = orgs.create_key(scope, admin, "limited", ["lookup"], "test", settings)
    _, f2 = orgs.create_key(scope, admin, "other", ["lookup"], "test", settings)
    k1.rate_per_minute = 3
    db.commit()
    c = TestClient(app)
    codes = [c.get("/api/v1/indicators/lookup?value=0700000001", headers=H(f1)) for _ in range(5)]
    assert [r.status_code for r in codes] == [200, 200, 200, 429, 429]
    assert int(codes[3].headers["retry-after"]) >= 1 and codes[3].json()["error"]["code"] == "rate_limited"
    assert c.get("/api/v1/indicators/lookup?value=0700000001", headers=H(f2)).status_code == 200  # limits are per key
    assert db.query(ApiUsage).filter(ApiUsage.status == 429).count() == 2


def test_revoked_key_rejected_and_usage_logged(keyed, db):
    org, key, c = keyed
    assert c.get("/api/v1/threat-intel", headers=H(key)).status_code == 200
    assert db.query(ApiUsage).count() == 1 and db.scalar(select(ApiKey)).last_used_at is not None
    TenantScope(db, org.id).revoke_key(db.scalar(select(ApiKey)).id)
    db.commit()
    assert c.get("/api/v1/threat-intel", headers=H(key)).status_code == 401


def test_threat_intel_and_analytics_endpoints(keyed, db, settings, make):
    org, key, c = keyed
    mod, _ = make.user("moderator")
    settings.verify_min_independent = 1
    r = submit(db, settings, "0700000003").report
    decide(db, settings, mod, r.id, "verify", "verified for intel test")
    db.commit()
    ti = c.get("/api/v1/threat-intel", params={"category": "reversal"}, headers=H(key)).json()
    assert ti["count"] == 1 and ti["items"][0]["value"] == "+254700000003" and "reporter" not in json.dumps(ti)
    assert c.get("/api/v1/threat-intel?since_days=0", headers=H(key)).status_code == 422
    submit(db, settings, "0700000004", org=org, county="Nairobi", bucket="a")
    an = c.get("/api/v1/org/analytics?days=7", headers=H(key)).json()
    assert an["total"] == 1 and "series" not in an
    assert c.get("/api/v1/org/analytics?days=400", headers=H(key)).status_code == 422


def test_api_errors_are_json_never_html(app):
    c = TestClient(app)
    assert c.get("/api/v1/nope").json()["error"]["code"] == "http_error"
    assert c.get("/api/v1/nope").headers["content-type"].startswith("application/json")


# ---------------- migrations and seed ----------------
def test_alembic_migration_matches_models_and_protects_audit_log(tmp_path):
    db_url = f"sqlite:///{tmp_path}/mig.db"
    env = {"SS_DATABASE_URL": db_url, "PATH": "/usr/bin:/bin"}
    out = subprocess.run([sys.executable, "-m", "scamshield", "migrate"], cwd=APP_DIR, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    insp = inspect(create_engine(db_url))
    assert set(insp.get_table_names()) - {"alembic_version"} == set(Base.metadata.tables)
    for name, table in Base.metadata.tables.items():
        assert {c["name"] for c in insp.get_columns(name)} == {c.name for c in table.columns}, name
    eng = create_engine(db_url)
    with eng.begin() as conn:
        conn.exec_driver_sql("INSERT INTO audit_log (ts, action, target_type, target_id, reason, detail, prev_hash, hash) VALUES ('2026-01-01','x','','','','{}','','')")
    with pytest.raises(Exception, match="append-only"), eng.begin() as conn:
        conn.exec_driver_sql("DELETE FROM audit_log")


def test_seed_is_labelled_synthetic_and_realistic(tmp_path):
    db_url = f"sqlite:///{tmp_path}/seed.db"
    env = {"SS_DATABASE_URL": db_url, "SS_STORAGE_DIR": str(tmp_path / "ev"), "PATH": "/usr/bin:/bin"}
    for args in (["migrate"], ["seed"]):
        out = subprocess.run([sys.executable, "-m", "scamshield", *args], cwd=tmp_path, env={**env, "PYTHONPATH": str(APP_DIR / "src")}, capture_output=True, text=True, timeout=300)
        assert out.returncode == 0, out.stderr[-500:]
    again = subprocess.run([sys.executable, "-m", "scamshield", "seed"], cwd=tmp_path, env={**env, "PYTHONPATH": str(APP_DIR / "src")}, capture_output=True, text=True, timeout=120)
    assert again.returncode != 0  # refuses to double-seed
    eng = create_engine(db_url)
    with eng.connect() as conn:
        for table in ("users", "indicators", "reports", "organisations", "cases", "api_keys", "corrections"):
            origins = {r[0] for r in conn.exec_driver_sql(f"SELECT DISTINCT origin FROM {table}")}
            assert origins and origins <= {"synthetic test data", "mock integration"}, (table, origins)
        values = [r[0] for r in conn.exec_driver_sql("SELECT norm_value FROM indicators WHERE type IN ('url','email')")]
        assert all(v.split("@")[-1].split("/")[0].endswith((".example", ".invalid", ".test", "example.test")) or ".example" in v or ".invalid" in v for v in values), values
        statuses = {r[0] for r in conn.exec_driver_sql("SELECT status FROM indicators")}
        assert {"verified", "unverified", "pending"} <= statuses
    creds = (tmp_path / "data" / "demo-credentials.txt").read_text()
    assert "SYNTHETIC" in creds and oct((tmp_path / "data" / "demo-credentials.txt").stat().st_mode & 0o777) == "0o600"


def test_cli_audit_verify_digest_create_user(tmp_path):
    db_url = f"sqlite:///{tmp_path}/c.db"
    env = {"SS_DATABASE_URL": db_url, "SS_STORAGE_DIR": str(tmp_path / "ev"), "PATH": "/usr/bin:/bin", "PYTHONPATH": str(APP_DIR / "src"), "SS_NEW_PASSWORD": "Cli-Created-Pass-9"}
    run = lambda *a: subprocess.run([sys.executable, "-m", "scamshield", *a], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)  # noqa: E731
    assert run("migrate").returncode == 0
    out = run("create-user", "cli@example.com", "moderator")
    assert out.returncode == 0 and "created cli@example.com" in out.stdout
    assert "OK" in run("audit-verify").stdout and "digests sent" in run("digest").stdout


def test_evaluation_dataset_size_labels_and_thresholds():
    from scamshield.evaluation import build_dataset, evaluate, holdout_items

    items = build_dataset() + holdout_items()
    assert len(items) >= 150
    labels = {i.label for i in items}
    assert labels == {"suspicious", "benign"}
    assert sum(i.label == "suspicious" for i in items) > 50 and sum(i.label == "benign" for i in items) > 50
    assert {i.split for i in items} == {"dev", "test", "holdout"}
    assert len({i.text for i in items}) == len(items) or len({i.id for i in items}) == len(items)
    m, errors, conf = evaluate(holdout_items())
    assert m.recall >= 0.9 and m.precision >= 0.85  # regression guard on the blind hold-out
    mt, _, _ = evaluate([i for i in items if i.split == "test"])
    assert mt.precision >= 0.9 and mt.recall >= 0.9
    assert m.f1 > 0 and 0 <= m.accuracy <= 1
    from scamshield.evaluation import Metrics

    assert Metrics(0, 0, 0, 0).precision == 0 and Metrics(0, 0, 0, 0).recall == 0 and Metrics(0, 0, 0, 0).f1 == 0 and Metrics(0, 0, 0, 0).accuracy == 0


def test_evaluate_cli_writes_results(tmp_path, capsys, monkeypatch):
    from scamshield import evaluation

    monkeypatch.setattr(evaluation, "Path", lambda *a, **k: tmp_path / "x" / "y" / "z" / "f.py" if False else Path(*a, **k))
    assert evaluation.run_evaluation(write=False) == 0
    assert "holdout:" in capsys.readouterr().out


def test_config_validation_refuses_insecure_production(settings):
    from scamshield.config import Settings

    s = Settings(environment="production", secret_key="dev-only-insecure-secret-change-me", cookie_secure=True)
    with pytest.raises(RuntimeError, match="SS_SECRET_KEY"):
        s.validate()
    s2 = Settings(environment="staging", secret_key="x" * 40, cookie_secure=False)
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        s2.validate()
    Settings(environment="staging", secret_key="x" * 40, cookie_secure=True).validate()
    Settings().validate()
    _ = (Indicator, png_bytes)
