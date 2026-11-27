# Deployment (staging only, nothing deployed)

Local run:
```
cd app && uv sync --all-groups
export SS_DATABASE_URL=sqlite:///./data/dev.db
uv run python -m scamshield migrate
uv run python -m scamshield seed          # SYNTHETIC demo data; credentials in data/demo-credentials.txt
uv run python -m scamshield serve --port 4300
```
Staging template: `Dockerfile` and `docker-compose.yml` (PostgreSQL 16) are written but NOT built or run here (no Docker on the dev machine). Required env: `SS_ENV=staging`, `SS_SECRET_KEY`, `SS_COOKIE_SECURE=true`, `SS_DATABASE_URL`, `SS_STORAGE_DIR` on a persistent encrypted volume. The app refuses to start in staging with the default secret or insecure cookies. Terminate TLS at a reverse proxy (HSTS is sent when secure). Health: `GET /healthz`. Scheduled job: `python -m scamshield digest` (cron hourly). Migrations: `python -m scamshield migrate` (Alembic).

Backup/restore: back up the database (`pg_dump` or `sqlite3 .backup`) and the evidence directory together, encrypted, at least daily; test restore monthly; after restore run `python -m scamshield audit-verify`. PostgreSQL has not been exercised on this machine: run the test suite against it before staging.
CI: `.github/workflows/ci.yml` is defined but was never pushed or executed on GitHub.
