# Design system

Source of truth: `design/design-tokens.css` (mirrored in `design-tokens.json`) and `design/components.css`. Gallery: `design/hifi/index.html`.

## Brand
**Name**: ScamShield Africa. **Tone**: calm, plain, factual. Never alarmist, never accusing.
**Logo concept**: a shield (protection) split into a teal field and a savannah-amber wedge (the amber is the "signal"), carrying a magnifier ring and tick-handle (check before you act). Works single colour. The prototype draws it as inline SVG (`logo()` in `app.js`). Wordmark in the system bold face with the tag line "Africa - Kenya pilot".
**Distinctiveness**: warm paper background (not cool grey), deep teal brand, amber signal, status chips with an icon plus text (never colour alone), verdict banners instead of a red "scam" badge, and an "evidence confidence" meter.

## Palette (contrast verified, see accessibility.md)
| Token | Light | Dark | Use |
|---|---|---|---|
| bg | #F6F2E8 | #0B1514 | page |
| surface | #FFFFFF | #13221F | cards |
| ink / ink-2 | #14201F / #44534F | #EAF1EE / #A9BDB8 | text |
| brand | #0B5A53 | #5CCBBB | actions, links |
| accent | #F2B134 | #F2B134 | prototype banner, badges, step highlight (text on it is #2B1D00) |
| risk-high | #A8211A on #FBE4E1 | #FF9A91 on #3B1816 | higher risk |
| risk-med | #8A5200 on #FCEBC8 | #F5BE5A on #3A2A0C | some warning signs, correction |
| ok | #17653A on #DDF1E4 | #7ED9A3 on #12301F | verified, few signs |
| unknown | #43505E on #E6E9EE | #B3BFCC on #243039 | unverified, not enough info |
| info | #1D55A0 on #E0ECFA | #9CC4FF on #162A44 | under review |
| focus | #1B4FD8 | #8FB0FF | 3px focus ring |
Dark mode follows `prefers-color-scheme`, overridable with `data-theme` (toggle in header).

## Typography
System stack (no web font download, helpful on mobile data): Segoe UI, system-ui, Roboto, Helvetica, Arial. Mono stack for indicator values. Scale: 13, 15, 17 (body), 20, 26, 34px. Line height 1.55 body, 1.2 headings. Body is never below 15px except 13px meta.

## Spacing, radius, touch
4/8/12/16/24/32/48/64px. Radius 6/12/20/pill. Minimum target 48px (44px for dense menus). Cards 1px line border with a light shadow.

## Components (all in components.css)
Buttons (primary, secondary, danger, ghost, small, block); text inputs, textarea, select, radio "choice" cards, checkboxes, switches; field with hint and inline error; error summary; status and risk **chips** (icon + text); **verdict banner**; **evidence-confidence meter**; result card; stepper; tabs; table that turns into labelled cards below 720px; KPI tile; notice (info, warn, error, ok); empty state; skeleton loader; spinner; dialog (centered on desktop, bottom sheet on mobile); toast; account menu; timeline; key-value list; code block; evidence placeholder; "Simulated" tag and "Synthetic demonstration data" chip.

## Icons
Own 24px set, 2px rounded stroke, drawn inline (shield, search, flag, spark, list, bell, user, grid, key, code, users, log, check, x, alert, info, moon, menu, queue, chart, case, download, plus, phone, link, mail, wallet, store, copy, lock, home). Always paired with text or an aria label.

## Charts
One accent series colour (teal), a second (burnt orange) only when two series exist, grid in a quiet tone, direct labels, SVG with an `aria-label` that states the trend, a text alternative below, no 3D or decorative charts. Bars have numeric labels. Small counts are replaced with "<5".

## Motion
160ms transitions; skeleton shimmer; all animation disabled under `prefers-reduced-motion`.

## Tokens
See the two files above. Names: `--bg --surface --surface-2 --ink --ink-2 --line --brand --brand-ink --brand-soft --accent --focus --risk-* --ok* --unknown* --info* --chart-*`, `--sp-1..8`, `--r-*`, `--fs-*`, `--tap`.
