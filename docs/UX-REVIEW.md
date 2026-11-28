# UX review

## Method
Ran the app with its synthetic seed data on a local port and captured every key screen with Playwright and the cached Chromium. Public screens were captured anonymously; moderator and organisation-admin screens signed in with seeded demo accounts. Desktop was 1280x800 and mobile 375x812, light and dark for a subset (home, results, indicator, moderation review, organisation dashboard). Screens were reviewed against the product design system, accessibility and trust/safety copy. Focus: public lookup and report flow on a cheap phone, moderator and organisation-analyst workspaces, trust and safety messaging.

## Findings
| Sev | Screen | Problem | Fix | Status |
|---|---|---|---|---|
| High | Organisation dashboard | The range selector used an inline `onchange` handler, which the CSP blocks, so changing the range did nothing | Replaced with `data-autosubmit` handled in `app.js` (no CSP change). Test added that no template has inline handlers | Fixed |
| High | Indicator record | Safety advice sat below a long record table on mobile, and there was no urgent guidance for someone who already paid | "What to do" now directly follows the verdict, plus an "Already sent money or shared a PIN?" block | Fixed |
| High | Home | No visible urgent help for a frightened user who has already lost money | Added a notice under the search box | Fixed |
| Medium | Search, no result | Three filters pushed the empty state below the fold, and the empty state gave no next steps | Filters collapsed into a details element (open when a filter is active); three concrete next steps added | Fixed |
| Medium | Moderator review | Reject and Restrict reporter submitted with one tap, and the decision panel was at the bottom on mobile | Confirmation prompt via `data-confirm`; "Jump to decision" link | Fixed |
| Medium | Organisation dashboard | Raw codes ("url", "phishing") in the charts | Mapped to the product's plain labels | Fixed |
| Low | Buttons | 44px touch target not guaranteed | `min-height:44px` for buttons and icon buttons | Fixed |
| Low | Org dashboard chart | Peak label is tiny on mobile (SVG text scales) | Round 2: replaced by a readable HTML caption | Fixed in round 2 |
| Low | Home | Demo "Try" links wrap awkwardly on mobile | Round 2: stacked list of 44px pills | Fixed in round 2 |
| Low | Moderator review | Eight actions in one form remain dense on mobile | Round 2: grouped with progressive disclosure, same form and values | Fixed in round 2 |

## Not reviewed
Swahili copy (draft, no native review), print styles, keyboard-only walkthrough and screen readers beyond reading the markup, the API docs page, admin screens, and performance measurement. Prototype in `design/prototype/` was not changed; it does not include these screens in the same form, so there is no new drift beyond the added home notice.

Before/after screenshots (mobile, light) are in `docs/screenshots/ux-review/`.

## Round 2

All checks below are automated in `app/e2e/` and run in CI with the other browser tests. Method: a seeded local server, Playwright with Chromium, every reachable screen for every role (anonymous, reporter, moderator, organisation analyst, organisation admin, platform admin), at 375px and 1280px, light and dark.

### Results
| Area | Before | After | Evidence |
|---|---|---|---|
| axe-core 4.14.1 (WCAG 2.0/2.1/2.2 A and AA plus best-practice), own screens | 0 critical, 6 serious (3 screens: scrollable regions without keyboard access on `/admin/roles` and `/dev/docs`), 7 moderate (Swahili notice outside a landmark) | 0 critical, 0 serious, 0 moderate | `e2e/test_a11y.py` |
| axe on `/docs` (bundled third-party Swagger UI) | 4 serious rule types (target size, nested controls, contrast, missing `lang`) | `lang` fixed; the other three remain inside Swagger UI | see "Still open" |
| Keyboard-only walkthrough | Found: report wizard stole focus to the step heading on page load, skipping the skip link and header | Fixed (focus moves only after Next/Back); 17 tests pass | `e2e/test_keyboard.py` |
| Contrast, text and form-control borders, 375px light and dark, 4 role groups, about 30 screens | no failures | no failures (axe and an independent computed-style sweep) | `e2e/test_contrast_print_perf.py` |
| Print (A4, `emulateMedia print`, PDF render) on org dashboard, cases, reports, exports, API docs, moderator review, audit, public record, search, about | navigation chrome, buttons and sticky table headers printed; dark card backgrounds | print stylesheet: chrome hidden, white background, borders instead of shadows, tables unclipped, a one-line provenance header | same test |
| Performance on the heaviest pages (home, search, report, org dashboard, moderator review, audit) at 375px | not measured | 7 requests per page, 6.6 to 39 KB transferred (39 KB is the cold first load including CSS, JS and icons; later pages reuse cache), CLS 0 on all. Enforced limits: CLS below 0.1, at most 12 requests, under 150 KB | same test (localhost, no throttling) |

### Changes
- Scrollable regions (`/admin/roles` table, code samples) are focusable, with a label on the table region.
- Swahili draft notice moved inside `main` so it is part of a landmark.
- Report wizard: no focus theft on load; "Step n of 5" text (announced politely) added to the progress bar.
- Org dashboard: peak is now a readable "Busiest day: N reports" caption; network-trend categories use the product's plain labels.
- Home: "Try a sample search" is a wrapping list of 44px targets; the "Already sent money?" notice no longer breaks into two columns.
- Moderator review: Accept and Verify stay in view; "Ask for more or tidy up" (mark unverified, request/attach evidence, merge) and "Reject or restrict" are collapsible groups on phones and open by default on wide screens. Same fields, same button names and values, same confirmation prompts. Buttons are full width on phones. The e2e helper opens the groups first.
- `/docs` sets `lang="en"`; `/dev/docs` says the explorer is third-party and carries the same information in plain form.
- Prototype (`design/prototype/`): matching try-links wrapping, "Already sent money?" notice, and grouped moderator actions. Prototype click-through script passes with no console errors. Still labelled "Simulated".

### Screens reviewed in round 2
Admin users, organisations and roles, audit log, API docs (`/dev/docs`, `/dev/usage`, `/docs`), org campaigns, reports, exports, alert rules, corrections, notifications, settings, MFA set-up and the Swahili home page at 375px (no horizontal overflow on any reviewed screen).

### Swahili check
All 18 catalogue keys exist in both languages and no template key is missing. Only the navigation, home heading, search and a few labels are translated; many strings on the same pages (card descriptions, the urgent notice, report form, every staff screen) are English, so pages mix languages. The draft notice already says it needs native review. **No native speaker has reviewed any Swahili text, and I did not add new Swahili strings.** Native review and translation of the remaining screens are required before a Swahili launch.

### Still genuinely open
- Real screen-reader testing (VoiceOver, NVDA, TalkBack), real low-end phones and real throttled networks were not done and are not claimed. The performance numbers are localhost only.
- `/docs` (Swagger UI, third-party bundle): target size, nested interactive controls and contrast are inside the library. It is excluded from the failing check apart from page language. It is also bright in dark mode.
- Moderator actions still use the browser's own confirm prompt (no custom dialog), so there is no modal to focus-trap; native prompts are keyboard accessible but unstyled.
- Swahili coverage and native review (above).
- Print was verified by emulation and PDF rendering, not on physical printers.

Screenshots: `docs/screenshots/ux-review/r2-*` (before and after, mobile, light).
