# Architecture

Modular monolith, Python 3.12 (uv), FastAPI, SQLAlchemy 2, Alembic, Jinja2 server-rendered pages, ~70 lines of vanilla JS (no CDN), SQLite for dev/test with a portable schema (PostgreSQL via `SS_DATABASE_URL`; compose file provided but NOT run here). The recommended stack was adopted unchanged: coverage.py gives measurable line+branch coverage and the analysis engine is Python.

```
web/ (routers: public, auth, staff, org+dev, api)  ->  services (reports, moderation, corrections, accounts, orgs, notify)
                                                    ->  critical rules (rules, normalize, similarity, analysis, permissions, security, uploads, audit, ratelimit, tenancy)
                                                    ->  models/db (SQLAlchemy)
```
- **Design reuse:** `design-tokens.css` and `components.css` are copied unmodified into `web/static`; icons and logo come from the prototype; screens follow `screen-specifications.md`.
- **Auth:** Argon2id, DB sessions (hashed token, HttpOnly, SameSite=Lax, Secure when configured), HMAC CSRF tokens bound to the session/anon cookie, TOTP with Fernet-encrypted secrets and recovery codes, lockout, rate limits (DB sliding window).
- **Tenant isolation:** all organisation data goes through `tenancy.TenantScope`; routes never build org queries.
- **Audit:** append-only hash-chained table; ORM hooks plus SQLite/PostgreSQL triggers block UPDATE/DELETE; `audit-verify` and `/audit?verify=1`.
- **Analysis:** transparent regex rules + MinHash similarity -> `{label, confidence, reasons, matched_prior_reports}`. `llm_adapter.py` is an optional interface, off by default, no provider connected, never called in tests.
- **Mail:** sandbox mailer writes to `mail_outbox` (labelled "mock integration"). No delivery.
- **Files:** magic bytes, size/pixel limits, re-encode (EXIF dropped), random names, stored outside web root, served only by an authorised endpoint.
- **Data origin:** `origin` column on every record table; seed labels everything "synthetic test data".
