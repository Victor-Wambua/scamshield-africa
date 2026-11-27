# Decisions on the design's open questions

All values are configurable (`app/.env.example`, `scamshield/config.py`).

1. **Verified with evidence.** Needs a moderator action AND (>= `SS_VERIFY_MIN_INDEPENDENT` (3) independent reporters OR a moderator-attached primary evidence item, `SS_VERIFY_ALLOW_MOD_EVIDENCE`). Independent = distinct accounts and distinct device/IP-hash buckets; reports are grouped transitively when they share an account or a bucket, each group counts once (`rules.independent_count`). Only moderator-accepted reports count. This replaces the design prototype's ">= 2 reporters and checked evidence" rule. Buckets are a salted hash of the /24 network plus the first 60 characters of the user agent; raw IPs are never stored. Limitation: people behind one shared network with the same browser string count once (conservative).
2. **Evidence visibility.** Raw evidence and full message text: submitter, moderators/platform admins, and the owning organisation's analysts for reports that organisation submitted. Never public. Enforced in `/evidence/{id}` and `TenantScope`, tested.
3. **Masking.** Lists show partial values (`+2547•• ••• 001`, `j•••@example.com`, host plus `/…`). An exact-match search shows the full value and status via a per-record token so ID enumeration cannot unmask. No reporter identity; no names of private individuals (business-name type is moderated).
4. **Correction SLA.** Immediate acknowledgement (sandbox email) and record marked "Disputed"; decision target `SS_CORRECTION_SLA_DAYS` = 7; urgent legal requests get a 1-day target, notify all platform admins and are audited. A different moderator must decide on records one verified; data removal (scrubs evidence files and report text) needs a platform administrator.
5. **i18n.** `locales/en.json` and `sw.json`. Swahili strings are a draft needing native review; the UI shows that notice.

## Evidence confidence formula
0.10 + 0.12 x min(independent,5) + 0.08 x min(evidence,3) + 0.20 if moderator primary evidence + 0.12 if verified, capped at 1.0 and at 0.40 while a correction is open. It measures support for the record, not fraud likelihood.

## Other choices
Moderators cannot review their own reports. Staff roles (moderator, org analyst/admin, platform admin) require TOTP (the design listed analyst as well). Account deletion anonymises the account but keeps reports (without contact data) so counts stay correct.
