# Wireframes

Visual files: `design/wireframes/index.html` (open in a browser). 12 sheets, 59 annotated frames, grayscale, with PNG exports in `design/wireframes/png/`. Desktop frames are 880px wide, mobile frames 320px wide. Numbered pins in a frame match the numbered notes beside it.

| Sheet | Covers | Notes |
|---|---|---|
| 01-auth | Login (mobile, desktop), register, password recovery, MFA | Email or phone; strength meter; identical recovery message whether or not the account exists; MFA for privileged roles |
| 02-onboarding-home | Three onboarding cards; public home mobile and desktop | Search is the hero; tab bar; verified warnings list |
| 03-search-detail | Results (m, d), not-reported state, record detail: verified/high, unverified, correction requested | Verdict banner, reasons, confidence, fields, history, advice; "not reported does not mean safe" |
| 04-report-flow | Six steps on mobile; details and review/consent on desktop | One question per mobile screen; error summary; saved answers on failure |
| 05-analyser | Input, result with highlights and reasons, desktop | Confidence level; reasons; not proof |
| 06-my-reports-correction | Status tracking (m, d), correction form, confirmation | Four-stage progress; reason radios; flagged record |
| 07-moderation | Queue (d, m), review, duplicate merge dialog, evidence-request sheet, corrections | Verify locked with reason; same-reporter handling |
| 08-institution | Analytics (d, m), campaigns, cases, exports, alert subscriptions | Suppression below 5; internal notes |
| 09-developer-portal | Keys, docs, usage, try-it (m) | Secret shown once; five endpoints |
| 10-notifications-settings | Preferences (d, m), profile and settings | SMS/WhatsApp disabled with reason |
| 11-platform-admin | Users, roles matrix, audit log | Reason on every change |
| 12-states | Empty, loading, error, success, offline, restricted/partial | One next action each |

## Layout principles shown
- Mobile: single column, 48px targets, sticky bottom tab bar, bottom-sheet dialogs, tables become labelled cards.
- Desktop: content max width 1180px (1360px with sidebar); decisions in a right-hand panel on review pages.
- Every list has empty, loading and error variants (sheet 12).
- Rebuild with `node tools/build-wireframes.mjs` then `node tools/export-wireframes.mjs`.
