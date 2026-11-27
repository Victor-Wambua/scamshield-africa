# ScamShield Africa

Product 1 of 10 in the product studio. An independent fraud-intelligence network for Kenya first: check a phone number, link, email, payment reference or wallet; report what you saw; let institutions investigate campaigns. It records reports about indicators and is not a public accusation list.

**Status: design phase only.** This repository contains the complete design package and a clickable prototype. There is no backend or application code. All demo data is synthetic demonstration data.

## Open the prototype
```
cd <studio-root>/scamshield-africa
python3 -m http.server 4300
# http://localhost:4300/design/prototype/index.html
```
Or open `design/prototype/index.html` directly. Use the amber "Viewing as" bar to switch roles. Everything simulated is labelled "Simulated — design prototype".

## Package map
| Path | What |
|---|---|
| `design/product-brief.md` | Users, problems, verified sources and mismatches, competitor scan, legal considerations, data availability |
| `design/user-journeys.md` | Six key journeys with success definitions |
| `design/information-architecture.md` | Sitemap, per-role navigation, Mermaid module diagram |
| `design/wireframes.md` + `design/wireframes/` | 59 annotated grayscale frames in 12 sheets (HTML + PNG) |
| `design/design-system.md`, `design-tokens.css/.json`, `components.css` | Brand, palette (light/dark), type, components, icons, charts |
| `design/hifi/index.html` | High-fidelity gallery: 10 screens, light/dark, desktop/mobile |
| `design/prototype/` | Clickable prototype (vanilla, no CDN) |
| `design/screen-specifications.md` | Per-screen spec |
| `design/responsive-design.md`, `accessibility.md`, `prototype.md`, `design-review.md` | Responsive rules, accessibility with real contrast results, prototype scope and simulations, review against the requirements with gaps and open questions |
| `design/screenshots/` | Screenshots (desktop and mobile, light and dark) |
| `docs/PROGRESS.md`, `STATUS.md` | Studio progress tracker and product status |
| `tools/` | Verification and build scripts |

## Rebuild and verify
Requires Node and Playwright with a Chromium (set `PW_DIR` to a folder containing `node_modules/playwright`, optionally `CHROME`). Serve on port 4300, then:
```
node tools/test-prototype.mjs       # click-through, console errors
node tools/contrast.mjs             # WCAG contrast of palette tokens
node tools/a11y-check.mjs           # basic accessibility checks
node tools/build-wireframes.mjs && node tools/export-wireframes.mjs
node tools/build-hifi.mjs
node tools/screenshots.mjs
```
