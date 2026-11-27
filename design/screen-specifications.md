# Screen specifications

Format per screen: purpose, route, roles, components, data, states, validation, copy. The prototype implements each (file `design/prototype/*.js`); where the production behaviour differs from the simulation it is noted as **Prod**.
Shared rules: every list has loading (skeleton), empty, error (recoverable) states. Every destructive or decision action uses a dialog with a required reason (min 8 characters) where noted. Copy keys are namespaced `screen.element` for Kiswahili.

## S1 Home and search `/`
Roles: all. Purpose: check an indicator. Components: hero search (label hidden but present for screen readers), example chips, three action cards, verified warnings (3), stay-safe tips. Data: top verified indicators. States: empty query blocked by `required`. Copy: "Check before you pay or reply." / "Not reported does not mean safe."
## S2 Results `/search`
Components: search, filters (type, status, risk), result cards. Data: indicator summary (value, type, status, risk, independent reports, last observed, category). Matching: normalise whitespace, dashes, +254 to 0; **Prod** adds fuzzy/URL normalisation. States: skeleton 450ms, no results (with and without filters), error ("simulate error" in the query) with retry. Sort: relevance then last observed (**Prod**).
## S3 Indicator record `/i/{id}`
Components: verdict banner, reasons, evidence-confidence meter + "how it is worked out", fields (type, risk category, first reported, last observed, independent reports, evidence count, verification status, source, ID), review history, safety advice, actions. Permissions: public sees independent count and a summary, not raw submissions or evidence; staff (moderator, admin, analyst) also see submission totals and moderator IDs. Never shown: reporter identity, evidence files, personal data of third parties. Variants: verified/high, unverified/medium, under review, correction requested, low information.
## S4 Report flow `/report`
Steps: 1 Type; 2 Details; 3 Evidence; 4 Consent; 5 Review; 6 Confirmation. Fields and validation:
- Type: required.
- Value: phone `^(\+?254|0)[17]\d{8}$` after stripping spaces/dashes; email RFC-lite; URL has a dot and TLD of 2+ characters, no scheme required; wallet at least 26 characters; others non-empty.
- Description: 20 to 2,000 characters. Date optional, not future. Amount optional, integer KES >= 0.
- Evidence: up to 5 images, 5 MB each (**Prod**: check magic bytes, re-encode, strip EXIF, virus scan); message text optional; redaction checkbox.
- Consent: privacy notice and truthfulness required; sharing with partners and follow-up contact optional and stored separately.
Duplicate logic: match on normalised value. New reporter on an existing indicator: +1 independent report. Same reporter again: +1 submission only, message "does not count as an independent report". No match: a new unverified record after review. Errors: summary with links to fields; submit failure ("simulate error" in the description) keeps all answers and offers retry. Success: reference `R-####`, next steps.
## S5 Message analyser `/analyse`
Input: 10 to 5,000 characters. Output: summary level (Several / Some / Few warning signs), analysis confidence (level and %), message with highlights (underline + colour), reasons per signal, comparison with prior indicators (phone and exact value match), disclaimer, actions. Rule signals: urgency, payment request, reversal story, prize, credential request, organisation named, unusual/shortened URL, advance fee. **Prod**: transparent rules + similarity, documented evaluation set, optional model adapter, model/version shown. Never says "this is a scam".
## S6 My reports `/mine` (reporter)
Cards with reference, value, date, four-stage progress (Received, Duplicate check, Moderator review, Outcome), view record, withdraw (dialog). Empty state with report CTA.
## S7 Correction request `/correct/{id}`
Fields: relationship (radio, 5), explanation >= 20 chars, contact email (valid), acknowledgement checkbox. Result: reference `C-##`, record flagged and wording softened. Permissions: anyone. **Prod**: ownership proof upload; rate limit per IP; different moderator than original.
## S8 Auth `/login /register /recover /mfa`
Login: email/phone + password; staff-looking emails continue to MFA in the prototype. Register: name, email/phone, password >= 10 chars with strength meter, terms checkbox. Recover: valid email, uniform confirmation. MFA: exactly 6 digits (**Prod**: TOTP, recovery codes, lockout after 3 failures). Roles needing MFA: moderator, analyst, org admin, platform admin.
## S9 Notifications `/notifications`
Category switches (reversal, phishing, investment, jobs, tax), event switches (new verified threat, emerging campaign, status change on my reports, org updates), channels (email on; SMS and WhatsApp disabled "after provider verification"), frequency (instant, daily, weekly), explicit Save with dirty indicator, recent list.
## S10 Settings `/settings`
Profile, language, MFA setup dialog, download my data, delete account dialog with reason.
## S11 Moderation queue `/mod`
KPIs (waiting, awaiting evidence, corrections, median time). Filter: needs action, decided, all; text search. Table columns: report, indicator, status, signals (same reporter, possible duplicate, priority), evidence count, received. Mobile: cards.
## S12 Report review `/mod/{id}`
Panels: submitted text, evidence, indicator record, possible duplicates, history; decision panel.
- **Verify**: allowed only if independent reporters >= 2 and checked evidence >= 1, else disabled with the reason shown; reason required.
- **Mark unverified**, **Request more evidence** (message to reporter), **Reject** (reason), **Merge as duplicate** (choose target; same reporter keeps count), **Restrict reporter** (reason).
Every action writes an audit entry and updates queue and public record.
## S13 Corrections `/mod/corrections`
Accept (record returns to unverified, confidence capped), Decline (reason), Remove data (legal; irreversible warning; second approver in **Prod**).
## S14 Audit `/audit`
Append-only list: time, actor, action, reason, chained hash. **Prod**: hash chain verification, filters, export.
## S15 Institution `/org/*`
Analytics: KPIs, reports-per-day line with 7/30/90 range, category bars (click to filter), county bars with suppression below 5. Campaigns: table and investigate dialog (linked indicators, create case). Cases: list, new case, notes dialog (internal), close/reopen. Exports: columns, scope; CSV never includes reporter identity or raw evidence; file starts with a synthetic-data comment; log. Alerts: rules by category (email), toggle, new rule. Tenant isolation required in **Prod**.
## S16 Developer `/dev/*`
Keys: table, create dialog (name required, scopes, environment: test enabled, live disabled "needs approval"), secret displayed once with Copy, revoke dialog. Docs: base URL, auth, rate limit, five endpoints (lookup, report submission, incident status, threat-intel, org analytics) with parameters, example response, error codes. Usage: KPIs and chart. Try: endpoint, value, simulate 200/404/429, shows curl and JSON.
## S17 Admin `/admin`, `/admin/roles`
Users table: change role (reason), restrict/restore (reason), MFA column. Roles matrix (read-only). Org approvals appear in audit (design placeholder).
## S18 States `/states`
Reference for loading, empty, error, success, offline, rate limit, restricted, partial data.
