# Security

## Controls implemented (each has automated tests)
Argon2id passwords and policy; lockout; TOTP MFA for staff; session cookies; CSRF on every state-changing form (parametrised test over 20 endpoints); CSP (no inline script), nosniff, frame deny, HSTS when secure; output escaping (XSS tests on report text, analysis, corrections, audit); parameterised ORM queries; upload abuse tests (PHP/SVG/PDF/polyglot/bomb/oversize/extra files); role x endpoint authorisation matrix (GET and POST); MFA gate; tenant isolation (service and HTTP); evidence authorisation; API key hashing, scopes, revocation, per-key rate limits; rate limits on report/login/search/analyse/correction/register/recover; append-only audit; uniform login/recovery responses; CSV formula-injection neutralisation; data export and account deletion.

## Scans (run locally, outputs in `docs/reports/`)
ruff: clean. mypy: no issues in 37 source files. bandit: 0 issues (B101 skipped, documented; two false positives annotated). pip-audit: no known vulnerabilities (editable project skipped).

## Manual checklist run
Authz matrix, tenant isolation, upload abuse, rate limit, CSRF, XSS rendering: executed as tests. Not done: external penetration test, TLS configuration review on a real host, dependency pinning review, secrets-manager integration.

## Unresolved risks (no claim of production readiness)
- TOTP codes can be replayed within the validity window (no used-step store).
- Rate limiting keys on a network/UA bucket; shared networks may be throttled together, and a determined attacker can rotate UA.
- Sandbox mailer: reset links and alerts are not delivered; invite links are shown to the admin once.
- Reporter independence is heuristic; coordinated abuse with many devices is not detected.
- No virus scanning of uploads (images are re-encoded, which removes active content).
- Evidence files are not encrypted at rest (rely on disk encryption); only TOTP secrets are field-encrypted.
- Single-process rate limiting/audit chain assume a single writer; PostgreSQL deployment needs advisory locking for the audit chain under concurrency.
- Swagger UI `/docs` needs inline script allowance on that path only.
- Kenya Data Protection Act 2019: considerations only (consent, minimisation, export/delete, masking). No compliance claim; legal review outstanding.
