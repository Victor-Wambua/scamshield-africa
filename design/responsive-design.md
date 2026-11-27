# Responsive design

Approach: mobile-first CSS in `components.css`; every public screen is designed for a 360px Android viewport first, then enhanced.

| Breakpoint | Layout |
|---|---|
| < 600px (phone) | Single column; bottom tab bar (first five nav items, 60px tall, safe-area padding); dialogs become bottom sheets; search is stacked (input above button); tables become labelled cards; demo banner shortens |
| 600-899px (tablet) | Search inline; grids to 2 columns; tab bar still at the bottom; tables show as tables from 720px |
| >= 900px (desktop) | Top nav for public roles; left sidebar (230px) for staff roles; content max 1180px (1360px with sidebar); decision panels sit right of content (2fr/1fr) |

Mobile-specific design (not a squeezed desktop): one question per screen in the report flow with a stepper; 48px controls; large "Search" and "Continue" buttons; example chips for fast testing; verdict banner above the fold on record pages; filters as stacked selects; no hover-only controls; no horizontal scrolling (checked at 375px: scroll width 375); data tables replaced by cards; skeletons rather than spinners; drafts survive a failed send; no web fonts or images, so pages stay small on mobile data.
Tablet: staff dashboards remain usable with the tab bar and cards; tap targets unchanged.
Print/export: not designed in v1.
Orientation: layouts reflow in landscape; nothing is fixed to a viewport height.
Verification: screenshots at 1280x860 and 390x844 in light and dark, 16 screens each (64 files) in `design/screenshots/`; automated check that the 375px home has no horizontal scroll.
