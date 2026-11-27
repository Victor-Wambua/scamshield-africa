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
| Low | Org dashboard chart | Peak label is tiny on mobile (SVG text scales) | Not fixed: needs a layout change | Open |
| Low | Home | Demo "Try" links wrap awkwardly on mobile | Not fixed | Open |
| Low | Moderator review | Eight actions in one form remain dense on mobile | Not fixed: would change the workflow | Open |

## Not reviewed
Swahili copy (draft, no native review), print styles, keyboard-only walkthrough and screen readers beyond reading the markup, the API docs page, admin screens, and performance measurement. Prototype in `design/prototype/` was not changed; it does not include these screens in the same form, so there is no new drift beyond the added home notice.

Before/after screenshots (mobile, light) are in `docs/screenshots/ux-review/`.
