# Design review

Reviewer: the design author, so this is a self-review. A founder or independent review is still needed. Date: 2026-11-27.

## 1. What was actually run
| Check | Result |
|---|---|
| Prototype click-through (`tools/test-prototype.mjs`, headless Chromium, desktop 1280 then mobile 375) | 46 assertions, 46 pass, 0 fail. Flows: search (hit, no hit, filter, error), record detail, analyser, report flow with validation, repeat-reporter rule, login/recover/MFA, my reports, correction, notification preferences, moderator verify/merge/evidence/reject/correction/audit, analyst range/filter/case/notes/CSV/alerts, developer key/try/docs, admin restrict/roles, role gating, theme, Kiswahili draft, states gallery, 375px layout |
| Console errors and warnings during the click-through | **None** |
| Palette contrast (`tools/contrast.mjs`) | 42 text/non-text pairs across light and dark, all pass (lowest text ratio 5.43:1) |
| Accessibility script (`tools/a11y-check.mjs`) | 23 of 23 routes pass labels/names/h1/main/duplicate-id checks; keyboard focus ring visible on 13 of 14 Tab stops (the other was the document body) |
| Horizontal scroll at 375px (home) | None (scroll width 375) |
| Screenshots | 64 PNG (16 screens x desktop/mobile x light/dark), plus a gallery capture, in `design/screenshots/`; 12 wireframe PNG sheets; viewed and fixed: demo bar height, focus ring on headings, hidden error messages being visible, wrapped tab label |
| Not run | Manual screen-reader test, real-device Android test, user testing, Safari/Firefox, slow-network test, legal review |

## 2. Requirements A-I
| Req | Designed | Prototype | Gaps |
|---|---|---|---|
| A Public reporting portal | All 8 type choices, evidence, consent, review, confirmation, mobile and desktop wireframes | Full 6-step flow with validation, error retry, duplicate message | Real upload validation, offline queue and Kiswahili copy are specified, not demonstrated. Business impersonation, ads and wallets share one generic form |
| B AI analysis | Confidence level and reasons, never proof, prior-report comparison | Rule-based simulated analyser, highlights, reasons, matches, disclaimer | Not a model; confidence is a demo formula; no evaluation set; similarity search not demonstrated |
| C Record fields | All required fields on record page and spec | Present (type, value, first reported, last observed, independent reports, evidence, status, confidence, risk, source, history) | Evidence references are counts, not browsable by staff |
| D Duplicate detection | Rules specified | Same indicator links; same reporter does not add an independent report (tested) | Only exact match; no fuzzy matching or campaign clustering logic |
| E Moderation | Queue, review, merge, evidence request, corrections, restrict, remove | All actions update UI state and audit log (tested) | Second approver for removal and appeals are not simulated; restrict reporter only logs |
| F Public search | Search, status, counts, reasons, updated date, advice | Done, with not-reported messaging | No sort control; no pagination; address/privacy review of free-text summaries is a process, not UI |
| G Institution | Analytics, categories, trends, counties with suppression, CSV, cases, notes, alerts | Implemented as above | "API access" is only linked via the developer role; org-admin user management is described but not a screen; no tenant switcher |
| H Developer API | Keys, docs, usage, try-it | Five endpoints documented; key create/revoke; sample responses | No downloadable OpenAPI file; docs are an HTML page, not a machine spec |
| I Notifications | Categories, events, channels, frequency | Preferences with dirty/save; SMS and WhatsApp disabled | No email template designs; no in-app inbox beyond a short list |
Also: challenge/correct (done), visible audit trails (staff view), MFA for privileged users (step demonstrated, TOTP setup is a placeholder).

## 3. Acceptance list
| Criterion | Status |
|---|---|
| Major screens have visual wireframes | Met (59 frames, 12 sheets) |
| Journeys documented | Met (6 plus supporting) |
| Navigation and IA defined | Met |
| Design system documented | Met |
| Desktop and mobile layouts demonstrated | Met (wireframes, hi-fi, screenshots) |
| Prototype covers primary workflows | Met for the six journeys, simulated |
| Error, loading, empty states | Met (states gallery and in-flow) |
| Detailed enough to implement without guessing | Partly. Screen specs and rules exist, but open policy questions below affect implementation |
| Distinct identity | Self-assessed as met: warm paper plus teal and amber, evidence-confidence meter and verdict banner. Independent judgement needed |
| Hi-fi built on tokens, light and dark | Met, but hi-fi frames are **static captures of the prototype views**, not separately authored screens, and cover 10 screens, not every screen |

## 4. Honest issues and outstanding work
1. **Source verification failed for both primary pages** (bot challenges). CA and INTERPOL figures are corroborated only by secondary summaries. A human should open the pages before any figure goes in marketing or investor material.
2. Competitor scan is thin: two sites opened (ScamAdviser, Google Safe Browsing); Truecaller refused the fetch; carrier details come from search summaries.
3. Legal considerations are design assumptions; the Data Protection Act text and regulator pages were not read. No compliance claim is made.
4. Kiswahili is a draft covering key labels only.
5. No manual accessibility or usability testing; the 13/14 focus check shows one tab stop that is not a control, not a defect confirmed either way.
6. The prototype keeps state in memory; reload resets it. The role switcher bypasses real auth.
7. The analyser's compare step only matches exact numbers and domains.
8. Wireframes are generated from a script (`tools/build-wireframes.mjs`), so they are consistent but stylised.
9. The hi-fi gallery uses iframes at half scale for overview; open each file for full size.
10. On mobile queue cards an empty "Signals:" label shows when a report has no signals (cosmetic, not fixed).
11. Text-size and zoom to 200% were designed for but not tested in a browser.

## 5. Open questions for the founder
1. Verification rule: is "2 independent reporters plus 1 checked evidence item, or an authorised source" right? Should verified contributors count with a higher weight, and by how much?
2. Who may see raw evidence: moderators only, or approved partners too? Retention period?
3. Should phone numbers ever be shown in full publicly, or partly masked (for example 0700 000 xxx), given SIM recycling and defamation risk?
4. Correction SLA (7 days assumed) and who decides legal removal: you, counsel, or a panel?
5. Which first institutional partners (telco, bank, regulator) and will the pilot use one tenant or several?
6. Pricing posture for institutions and API (free tier limits)?
7. Name, domain and brand: is "ScamShield Africa" cleared, and is the amber/teal identity acceptable?
8. Kiswahili first-class at launch, and Sheng or other local languages later?
9. Do you want an official-data adapter (URL reputation lists, blockchain explorers) in the MVP, subject to terms?
10. Will the team accept the AI approach in the spec (transparent rules plus similarity, optional model adapter) for Phase B?
