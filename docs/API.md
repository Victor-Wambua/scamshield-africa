# API v1

Interactive OpenAPI: `/docs` (Swagger UI bundled locally) and `/openapi.json`. Auth: `Authorization: Bearer ssk_...` (or `X-API-Key`). Keys belong to one organisation, are shown once, stored as SHA-256, scoped (`lookup`, `report`, `intel`, `analytics`), revocable, rate-limited per key (default 60/min; 429 with `Retry-After`). Only test keys can be created.

| Endpoint | Scope | Notes |
|---|---|---|
| `GET /api/v1/indicators/lookup?value=&type=` | lookup | exact match; `found:false` is not safety |
| `POST /api/v1/reports` | report | owned by your org; one key = one independence bucket |
| `GET /api/v1/reports/{ref}/status` | report | your organisation's reports only |
| `GET /api/v1/threat-intel?category=&since_days=` | intel | verified indicators, exact values, no reporter data |
| `GET /api/v1/org/analytics?days=` | analytics | your own reports, county counts < 5 suppressed |

Errors are JSON `{"error":{"code","message"}}`: 401 unauthorized, 403 forbidden (scope), 404, 422, 429. Example: `curl -H "Authorization: Bearer $KEY" "http://127.0.0.1:4300/api/v1/indicators/lookup?value=%2B254700000001"`.
