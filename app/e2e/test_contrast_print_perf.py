"""Programmatic contrast sweep (WCAG 2.2 AA), print-media checks and page-weight / layout-shift measurements.

Performance numbers are measured on localhost with Chromium; any throttling is emulated, not a real network.
"""

from __future__ import annotations

import json

import pytest
from a11y_support import SEED_BASE, seeded_server, sign_in

pytestmark = pytest.mark.e2e

CONTRAST_JS = """() => {
  const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return {r:p[0], g:p[1], b:p[2], a:p.length > 3 ? p[3] : 1}; };
  const lum = ({r,g,b}) => { const f = v => { v/=255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); }; return .2126*f(r)+.7152*f(g)+.0722*f(b); };
  const blend = (fg, bg) => ({r: fg.r*fg.a + bg.r*(1-fg.a), g: fg.g*fg.a + bg.g*(1-fg.a), b: fg.b*fg.a + bg.b*(1-fg.a), a: 1});
  const bgOf = el => { const layers = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a === 1) break; } }
    let base = {r:255,g:255,b:255,a:1}; for (let i = layers.length - 1; i >= 0; i--) base = blend(layers[i], base); return base; };
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const n = walker.currentNode; if (!n.textContent.trim()) continue; const el = n.parentElement;
    if (!el || seen.has(el)) continue; seen.add(el);
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    if (cs.visibility === 'hidden' || cs.display === 'none' || r.width === 0 || r.height === 0 || el.closest('[hidden],.sr-only,svg,script,style')) continue;
    if (cs.backgroundImage !== 'none') continue;
    const bg = bgOf(el); let fg = parse(cs.color); if (!fg) continue; fg = blend(fg, bg);
    const a = lum(fg) + .05, b = lum(bg) + .05; const ratio = Math.max(a, b) / Math.min(a, b);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700; const large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    if (ratio < need) out.push({text: n.textContent.trim().slice(0, 40), cls: el.className, ratio: Math.round(ratio*100)/100, need});
  }
  return out;
}"""

UI_JS = """() => {
  const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return {r:p[0], g:p[1], b:p[2], a:p.length > 3 ? p[3] : 1}; };
  const lum = ({r,g,b}) => { const f = v => { v/=255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); }; return .2126*f(r)+.7152*f(g)+.0722*f(b); };
  const bgOf = el => { for (let e = el.parentElement; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a === 1) return c; } return {r:255,g:255,b:255,a:1}; };
  const out = [];
  document.querySelectorAll('input[type=text],input[type=search],input[type=email],input[type=password],input[type=number],input[type=date],select,textarea').forEach(el => {
    const r = el.getBoundingClientRect(); if (!r.width || el.closest('[hidden]')) return;
    const cs = getComputedStyle(el); const bd = parse(cs.borderTopColor); if (!bd || cs.borderTopWidth === '0px') { out.push({el: el.id || el.name, why: 'no border'}); return; }
    const a = lum(bd) + .05, b = lum(bgOf(el)) + .05; const ratio = Math.max(a, b) / Math.min(a, b);
    if (ratio < 3) out.push({el: el.id || el.name, ratio});
  });
  return out;
}"""

SCREENS = {
    "anon": ["/", "/search?q=0700000001", "/search?q=nothing-reported-here", "/report", "/analyse", "/about", "/login"],
    "moderator@demo.example": ["/mod", "/mod/10", "/mod/corrections", "/audit"],
    "orgadmin@bank.demo.example": ["/org", "/org/cases", "/org/reports", "/org/exports", "/dev", "/dev/docs", "/org/alerts"],
    "admin@demo.example": ["/admin", "/admin/orgs", "/admin/roles"],
}


@pytest.fixture(scope="module")
def env(browser):
    with seeded_server() as srv:
        yield {"srv": srv, "browser": browser}


def test_text_and_control_contrast_light_and_dark(env):
    failures = []
    for scheme in ("light", "dark"):
        for who, paths in SCREENS.items():
            ctx = env["browser"].new_context(viewport={"width": 375, "height": 812}, color_scheme=scheme, base_url=SEED_BASE, user_agent=f"contrast-{who}-{scheme}")
            page = ctx.new_page()
            if who != "anon":
                sign_in(page, who, env["srv"]["creds"])
            for path in paths:
                page.goto(path)
                page.wait_for_load_state()
                for f in page.evaluate(CONTRAST_JS) + page.evaluate(UI_JS):
                    failures.append((scheme, path, f))
            ctx.close()
    assert not failures, json.dumps(failures[:25], indent=1)


PRINT_PAGES = {
    "orgadmin@bank.demo.example": ["/org", "/org/cases", "/org/cases/1", "/org/reports", "/org/exports", "/dev/docs"],
    "moderator@demo.example": ["/mod/10", "/audit"],
    "anon": ["/i/1", "/search?q=0700000001", "/about"],
}


def test_print_media_is_a_plain_document(env):
    for who, paths in PRINT_PAGES.items():
        ctx = env["browser"].new_context(viewport={"width": 794, "height": 1123}, base_url=SEED_BASE, user_agent=f"print-{who}")
        page = ctx.new_page()
        if who != "anon":
            sign_in(page, who, env["srv"]["creds"])
        for path in paths:
            page.goto(path)
            page.emulate_media(media="print")
            hidden = page.evaluate("['.topbar','.tabbar','.side','.demo-bar'].every(s => { const e = document.querySelector(s); return !e || getComputedStyle(e).display === 'none'; })")
            assert hidden, f"navigation chrome shows when printing {path}"
            assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(255, 255, 255)"
            over = page.evaluate("[...document.body.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 5).map(e => e.tagName + '.' + e.className)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"horizontal overflow in print layout {path}: {over}"
            assert page.evaluate("getComputedStyle(document.querySelector('main'), '::before').content").startswith('"ScamShield Africa')
            pdf = page.pdf(format="A4")
            assert pdf[:4] == b"%PDF"
        ctx.close()


def test_page_weight_requests_and_layout_shift(env):
    heavy = {"anon": ["/", "/search?q=0700000001", "/report"], "orgadmin@bank.demo.example": ["/org"], "moderator@demo.example": ["/mod/10", "/audit"]}
    results = {}
    for who, paths in heavy.items():
        ctx = env["browser"].new_context(viewport={"width": 375, "height": 812}, base_url=SEED_BASE, user_agent=f"perf-{who}")
        page = ctx.new_page()
        if who != "anon":
            sign_in(page, who, env["srv"]["creds"])
        for path in paths:
            page.add_init_script("window.__cls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({type: 'layout-shift', buffered: true});")
            page.goto(path)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(300)
            m = page.evaluate("""() => { const nav = performance.getEntriesByType('navigation')[0]; const res = performance.getEntriesByType('resource');
                return {requests: res.length + 1, bytes: nav.transferSize + res.reduce((a, r) => a + r.transferSize, 0), cls: window.__cls}; }""")
            results[path] = m
            assert m["cls"] < 0.1, f"layout shift {m} on {path}"
            assert m["requests"] <= 12, f"too many requests {m} on {path}"
            assert m["bytes"] < 150_000, f"page weight {m} on {path}"
        ctx.close()
    print("PERF", json.dumps(results))
