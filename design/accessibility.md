# Accessibility

Target: WCAG 2.2 level AA. Status: design and prototype checked with automated scripts only. **No manual screen-reader (TalkBack, VoiceOver, NVDA) or user testing has been done**; that is an outstanding item.

## Contrast results (computed, `node tools/contrast.mjs`)
Relative luminance per WCAG 2.x. Text pairs need 4.5:1, focus ring 3:1. Result: **42 pairs checked, 0 failing**.

| Theme | Pair | Ratio | Needed | Result |
|---|---|---|---|---|
| light | ink on bg | 14.95:1 | 4.5:1 | PASS |
| light | ink on surface | 16.72:1 | 4.5:1 | PASS |
| light | ink2 on bg | 7.24:1 | 4.5:1 | PASS |
| light | ink2 on surface | 8.09:1 | 4.5:1 | PASS |
| light | ink2 on surface2 | 6.73:1 | 4.5:1 | PASS |
| light | brand on bg | 7.22:1 | 4.5:1 | PASS |
| light | brand on surface | 8.07:1 | 4.5:1 | PASS |
| light | brandInk on brand | 8.07:1 | 4.5:1 | PASS |
| light | brandSoftInk on brandSoft | 9.40:1 | 4.5:1 | PASS |
| light | accentInk on accent | 8.69:1 | 4.5:1 | PASS |
| light | riskHigh on riskHighBg | 5.97:1 | 4.5:1 | PASS |
| light | riskMed on riskMedBg | 5.43:1 | 4.5:1 | PASS |
| light | ok on okBg | 6.01:1 | 4.5:1 | PASS |
| light | unknown on unknownBg | 6.77:1 | 4.5:1 | PASS |
| light | info on infoBg | 6.14:1 | 4.5:1 | PASS |
| light | riskHigh on surface | 7.25:1 | 4.5:1 | PASS |
| light | ok on surface | 7.10:1 | 4.5:1 | PASS |
| light | focus on bg | 5.95:1 | 3:1 | PASS |
| light | focus on surface | 6.65:1 | 3:1 | PASS |
| light | ink on riskHighBg | 13.76:1 | 4.5:1 | PASS |
| light | ink on riskMedBg | 14.22:1 | 4.5:1 | PASS |
| dark | ink on bg | 16.19:1 | 4.5:1 | PASS |
| dark | ink on surface | 14.35:1 | 4.5:1 | PASS |
| dark | ink2 on bg | 9.42:1 | 4.5:1 | PASS |
| dark | ink2 on surface | 8.35:1 | 4.5:1 | PASS |
| dark | ink2 on surface2 | 7.25:1 | 4.5:1 | PASS |
| dark | brand on bg | 9.47:1 | 4.5:1 | PASS |
| dark | brand on surface | 8.40:1 | 4.5:1 | PASS |
| dark | brandInk on brand | 8.64:1 | 4.5:1 | PASS |
| dark | brandSoftInk on brandSoft | 10.61:1 | 4.5:1 | PASS |
| dark | accentInk on accent | 8.69:1 | 4.5:1 | PASS |
| dark | riskHigh on riskHighBg | 7.74:1 | 4.5:1 | PASS |
| dark | riskMed on riskMedBg | 8.17:1 | 4.5:1 | PASS |
| dark | ok on okBg | 8.41:1 | 4.5:1 | PASS |
| dark | unknown on unknownBg | 7.22:1 | 4.5:1 | PASS |
| dark | info on infoBg | 8.11:1 | 4.5:1 | PASS |
| dark | riskHigh on surface | 8.06:1 | 4.5:1 | PASS |
| dark | ok on surface | 9.67:1 | 4.5:1 | PASS |
| dark | focus on bg | 8.68:1 | 3:1 | PASS |
| dark | focus on surface | 7.70:1 | 3:1 | PASS |
| dark | ink on riskHighBg | 13.79:1 | 4.5:1 | PASS |
| dark | ink on riskMedBg | 12.08:1 | 4.5:1 | PASS |

Not covered by the script: the grey "line" border colour is decorative (inputs use the ink-2 border at about 7:1); the amber banner uses #2B1D00 text (8.69:1, listed above); text over any future photography.

## Design measures
- **Colour is never the only signal**: status and risk chips pair colour with an icon and words; highlights in the analyser are underlined; charts have text labels and an aria-label that states the trend.
- **Keyboard**: every control is a native button, link, input, select, details or dialog; skip link; logical order; native `<dialog>` traps focus and closes on Escape; account menu opens on Enter/Space, closes on Escape and returns focus to its button.
- **Focus**: 3px solid focus ring, 2px offset, in a colour with 3:1 or better against both backgrounds (light 5.95:1 on bg, dark 8.68:1). Programmatic focus on the page heading after navigation (no ring on the heading) and a live region announces "Page loaded".
- **Forms**: visible labels; hints linked with `aria-describedby`; inline errors with an icon and words, `aria-invalid`, an error summary that receives focus with links to the fields; required fields marked in words; autocomplete off only where inappropriate; password never blocked from paste.
- **Targets**: 48px minimum (WCAG 2.2 target size is 24px minimum; we exceed it). 
- **Reduced motion**: all animation and transition durations collapse under `prefers-reduced-motion`; skeleton shimmer is disabled.
- **Zoom and text size**: rem-based type, fluid layouts, no fixed heights on text containers; no horizontal scroll at 375px.
- **Plain language**: short sentences, no jargon, "reported / unverified / verified with evidence", reasons in one sentence each. Reading level target: age 12. Swahili: copy keys exist; a draft Kiswahili toggle covers key labels only and **needs native review**.
- **Dark mode**: separate token set verified for contrast; follows the system, user override available.
- **Low bandwidth and low literacy**: no web fonts, no images, icons plus words.
- **Dialogs**: labelled by their heading, reason fields have error text, focus returns after close.
- **Live regions**: toasts (polite), search count, analysis result, errors use role=alert.

## Automated checks run (`node tools/a11y-check.mjs`, headless Chromium, desktop)
- 23 routes across roles: exactly one h1 and one main, every input/select/textarea has a label or aria-label, every button/link has a name, no duplicate ids. **23 of 23 pass.**
- Keyboard: 14 Tab presses on the home page gave 14 distinct stops; a visible focus ring on 13 of 14, and the other stop was the document body (not a control).
- Reduced motion emulation: skeleton animation resolves to `none`.
Limits: these scripts do not prove screen-reader behaviour, reading order in every state, or colour-blind legibility.

## Outstanding
Manual testing with TalkBack on a mid-range Android, VoiceOver, keyboard-only on Windows; Kiswahili review; captions for any future video; accessible CAPTCHA alternative if bot protection is added (avoid image CAPTCHAs); formal VPAT-style statement not made.
