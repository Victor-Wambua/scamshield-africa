# Prototype

Location: `design/prototype/` (vanilla HTML, CSS, JS; no CDN, no build step, no network calls).

## How to open
Double-click `design/prototype/index.html`, or serve the repository and open the page:
```
cd <studio-root>/scamshield-africa
python3 -m http.server 4300
# open http://localhost:4300/design/prototype/index.html
```
Use the amber bar at the top: **Viewing as** switches Visitor, Registered reporter, Moderator, Organization analyst, Developer (org), Platform administrator; **Reset demo** restores seed data. A "Simulated — design prototype" label is always visible, and synthetic data is labelled "Synthetic demonstration data".

## Scope (what you can do)
- Navigation between about 30 routes, role-specific navigation, mobile tab bar, desktop sidebar, account menu, theme toggle (light/dark), language toggle (English / draft Kiswahili for key labels).
- **Public**: home search; results with type/status/risk filters; not-reported state; error state (type "simulate error"); indicator record with verdict, reasons, confidence meter, history; report flow (6 steps) with validation; analyser; my reports with withdraw dialog; correction request; login, register (password meter), recover, MFA step; notification preferences; settings with dialogs; UI states gallery.
- **Moderator**: queue with filter/search; review page; verify (locked until policy criteria met), mark unverified, request evidence, reject, merge duplicate, restrict reporter; correction queue (accept, decline, remove data); audit log that grows with every action.
- **Analyst**: analytics with 7/30/90 range and category filter, county suppression, campaigns with investigate dialog, case creation and notes, CSV download of synthetic data, alert rules.
- **Developer**: key creation (secret shown once), revoke, docs for five endpoints, usage, try-a-request with 200/404/429.
- **Admin**: user table with role change and restrict (reason dialogs), roles matrix, audit log.

## What is simulated (nothing here is real)
| Area | Simulation |
|---|---|
| Data | All indicators, reports, campaigns, counties, cases, users, keys, usage numbers and the 90-day series are invented. Numbers like 0700 000 xxx, domains on `.example`/`.test`, fake wallet |
| Accounts and auth | Any non-empty login works; MFA accepts any 6 digits; the role switcher is a shortcut. No passwords or sessions exist |
| Server | State lives in memory and resets on reload. No requests leave the page; no email, SMS or WhatsApp is sent |
| AI analyser | Keyword and regex rules plus exact-match lookup against sample data; **not a model**. Confidence is a formula for the demo and is not calibrated |
| Duplicate detection | Exact match on normalised value; one simulated reporter identity |
| Evidence upload | File names only; nothing is uploaded or scanned |
| Verification criteria | The 2 independent + 1 evidence rule is a design proposal, to be confirmed with the founder |
| API | Responses are static JSON or derived from sample data; no keys are issued; "live" environment is disabled |
| Exports | A CSV is generated in the browser from sample data |
| Notifications, case sharing, alerts | Toggles change local state only |
| Kiswahili | Draft machine-quality strings for key labels only |
| Statistics | No external statistic appears as fact; dashboard numbers are synthetic |

## Files
`index.html`; `data.js` (synthetic data); `app.js` (shell, router, dialogs, icons); `public.js` (public screens and flows); `staff.js` (moderation, institution, developer, admin); `design-tokens.css` and `components.css` (copies of `design/` sources, so the folder is self-contained).

## Known prototype limits
Hash routing only; no deep-link restoration of dialog state; the role resets to Visitor on reload; printing not designed.
