# Coverage

Command: `cd app && uv run pytest --cov=scamshield --cov-branch --cov-report=term-missing`.
**Critical business-rules modules** (line+branch, combined): normalize, similarity, analysis, rules, permissions, security, uploads, audit, ratelimit, tenancy, reports, moderation, corrections, accounts, orgs, notify. Result: **99.65 %** (each module >= 98.7 %).
**Overall** (all modules incl. web routers, CLI, seed, evaluation): **98 %** (3,407 statements, 774 branches). Unmeasured: the browser e2e tests and subprocess CLI runs. Uncovered lines are mostly defensive redirects in web routers.
Defensive code that could not be reached was removed rather than excluded; no `pragma: no cover` is used in critical modules.
