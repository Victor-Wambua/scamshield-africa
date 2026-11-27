# Acceptance report

Verification date 2026-11-27. Numbers below come from commands run in this session. Not production ready.
Tests: 278 pytest (all pass) + 6 Playwright e2e (all pass). ruff, mypy clean. bandit 0 issues. pip-audit 0 known vulnerabilities. Coverage: critical modules 99.65 %, overall 98 %.

## Product acceptance list
| Criterion | Status | Evidence |
|---|---|---|
| Reports submitted and stored securely | Met | `test_web_public` report flow, e2e journey 1; hashed buckets, no raw IP |
| Evidence uploads validated | Met | `test_uploads_*`, `test_upload_abuse_over_http` (magic bytes, size, re-encode, EXIF) |
| Duplicates identified | Met | `test_duplicate_detection_normalised_*`, similarity tests, e2e merge |
| Analysis explainable | Met (limited accuracy) | reasons/confidence/prior matches; EVALUATION.md (synthetic) |
| Moderators review/correct | Met | `test_reports_moderation`, `test_corrections_*`, e2e correction |
| Public search appropriate | Met | masking/leak tests, safety advice, no evidence public |
| Users can challenge records | Met | correction flow + SLA + urgent legal |
| Institutional isolation | Met | `test_tenancy_isolation`, `test_org_isolation_http`, e2e isolation |
| API authenticated and rate-limited | Met | `test_api_*`, e2e key lifecycle |
| Audit trails | Met | hash chain, DB triggers, tests |
| Automated tests cover critical workflows | Met | above |
| MVP: >= 95 % critical-rule coverage + separate overall | Met | 99.65 % / 98 % |
| MVP: no unresolved critical/high vulnerabilities | Partially | scans clean; no external pentest; residual risks in SECURITY.md |
| Documented AI evaluation | Met (synthetic, optimistic) | EVALUATION.md |
| Functional institutional dashboard | Met | analytics, CSV, cases, notes, alerts |
| Verified/Reported rule per Decision 1, privacy per 2-3, SLA per 4, i18n per 5 | Met | DECISIONS.md + tests |
| SMS/WhatsApp, live LLM, national data | Not met (external) | documented as outstanding |

## Universal list
Critical journeys work: Met (e2e). Data persists: Met (SQLite, migrations tested). Business logic tested: Met. Authn+authz: Met (matrix). Critical data protected: Partially (evidence not encrypted at rest). Error handling: Met (error pages, JSON API errors). Reports from actual data: Met (analytics from DB, synthetic labelled). APIs documented: Met (/docs). Tests executed: Met. No unresolved critical security issues: Partially (see above). Deployable to staging: Partially (Dockerfile/compose written, NOT built or run; PostgreSQL untested). Docs complete: Met. Known limitations disclosed: Met. Pilot plan: Met (PILOT.md). Business and impact metrics defined: Met (defined, none measured).

## Design fidelity
Fresh screenshots of the real app (60 files, light/dark, desktop/mobile) in `docs/screenshots/`. Compared home, record, review against `design/screenshots`; the home page was corrected (cards, example links, two-column layout). Remaining deviations: no prototype demo bar or role switcher (intended), verified-list cards simplified, "states" gallery and in-app API console not built (KNOWN-LIMITATIONS). Not all 60 screenshots were individually compared.
