# User journeys

All journeys are demonstrated in the prototype (`design/prototype/index.html`). Success definitions are measurable targets for the pilot, not results.

## J1. Report a scam from a phone (consumer, Android, mobile data)
Trigger: a caller asked for "money sent by mistake" to be returned.
1. Open app/web, tap **Report** (tab bar). 2. Choose "Phone number or call". 3. Enter number and what was said; inline format check. 4. Optionally attach screenshot or paste text; tick "removed personal details". 5. Read plain-language privacy summary; tick two required boxes. 6. Review; **Send**. 7. Confirmation with reference, duplicate outcome, prompt to register to track.
Edge states: validation summary; network failure keeps answers and offers retry; offline notice.
**Success**: report submitted in under 3 minutes; the user understands what happens next; no personal data of the reporter is published; a repeat submission by the same person is linked and not counted as independent.

## J2. Check a suspicious number or link before paying
1. Home search; paste value. 2. Results list with status and risk chips. 3. Open record: verdict banner, reasons, evidence confidence, record fields, history, advice. 4. Decide; optionally report or request correction. Empty result says "Not reported does not mean safe" and offers Report and Analyse.
**Success**: user reaches a record or a clear empty state in under 10 seconds; can state why the record is rated as it is; never sees an accusation of a named person.

## J3. Moderator review and duplicate merge
1. Sign in with MFA. 2. Queue shows signals (same reporter, possible duplicate, priority). 3. Open report: text, evidence, indicator record, duplicates, history. 4. Decide: verify (locked until 2 independent reporters and 1 checked evidence item, reason displayed), mark unverified, request evidence, reject, restrict reporter, or **merge** into an existing record choosing the target. 5. Every action asks for a reason and writes to the audit log; the public record updates.
**Success**: decision in under 2 minutes for a clear case; merging a same-reporter repeat leaves the independent count unchanged and says so; audit entry exists for every action.

## J4. Correction or challenge request
1. On a record choose "This looks wrong. Request a correction". 2. Pick relationship (owner, impersonated, personal info, legal, other), explain, give contact email, acknowledge false-claim notice. 3. Receive reference; record is marked "Correction requested" with softened wording. 4. A moderator accepts (record returns to unverified, confidence capped), declines with reason, or removes data (legal; second approver in production). 5. Requester notified.
**Success**: acknowledged immediately; decision target 7 days; every outcome logged; wrongly labelled owner can see the outcome.

## J5. Institution analyst investigates a campaign and exports
1. Sign in with MFA; dashboard shows reports per day and categories; change range. 2. Open Campaigns, **Investigate** "Fake M-PESA reversal"; see linked indicators. 3. Create a case; add internal notes (visible only inside the organisation). 4. Exports: pick columns and scope, download CSV (no reporter identity, no raw evidence). 5. Subscribe to alert rules.
**Success**: from login to exported CSV in under 5 minutes; small counties show "<5"; export logged.

## J6. Developer gets an API key and does a lookup
1. Developer portal, **Create key** (name, scopes, test environment). 2. Secret displayed once with Copy. 3. Docs list the five endpoints with parameters, examples, error codes. 4. "Try a request" shows curl and JSON for 200, 404, 429.
**Success**: first successful lookup in under 10 minutes; secret never shown again; revocation works.

## Supporting journeys
Register/sign in/recover/MFA (`/login`, `/register`, `/recover`, `/mfa`); analyse a message; track my reports; notification preferences; admin user and role changes.
