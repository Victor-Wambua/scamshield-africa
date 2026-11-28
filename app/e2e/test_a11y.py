"""Automated accessibility pass: axe-core over every reachable screen, per role, 375/1280px, light/dark.

axe-core is vendored under e2e/vendor (dev/test only, MPL-2.0, never served by the app).
Fails on any serious or critical violation. Set A11Y_REPORT=1 to print every violation.
"""

from __future__ import annotations

import os

import pytest
from a11y_support import AXE, ROLES, SEED_BASE, screens, seeded_server, sign_in
from sqlalchemy import select

from scamshield.models import Case, Indicator, Report

pytestmark = pytest.mark.e2e
VIEWPORTS = {"375": {"width": 375, "height": 812}, "1280": {"width": 1280, "height": 800}}


def run_axe(page) -> list[dict]:  # type: ignore[no-untyped-def,type-arg]
    page.add_script_tag(content=AXE.read_text())
    return page.evaluate("axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}).then(r => r.violations.map(v => ({id:v.id, impact:v.impact, n:v.nodes.length, sample:v.nodes.slice(0,2).map(n => n.html.slice(0,140)), help:v.help})))")


def collect(browser) -> list[tuple[str, str, str, str, dict]]:  # type: ignore[type-arg]
    found = []
    with seeded_server() as srv:
        with srv["db"].factory() as s:
            ids = {"ind": s.scalars(select(Indicator.id).order_by(Indicator.id)).first(), "rep": s.scalars(select(Report.id).order_by(Report.id)).first()}
            case = s.scalars(select(Case.id).order_by(Case.id)).first()
            ids["case"] = case  # type: ignore[assignment]
        for role, email in ROLES.items():
            for scheme in ("light", "dark"):
                for vpname, vp in VIEWPORTS.items():
                    ctx = browser.new_context(viewport=vp, color_scheme=scheme, base_url=SEED_BASE, bypass_csp=True, user_agent=f"a11y-{role}-{scheme}-{vpname}")
                    page = ctx.new_page()
                    if email:
                        sign_in(page, email, srv["creds"])
                    for path in screens(role, ids):
                        page.goto(path)
                        page.wait_for_load_state()
                        for v in run_axe(page):
                            found.append((role, f"{scheme}/{vpname}", path, v["impact"], v))
                    ctx.close()
    return found


def test_axe_no_serious_or_critical_violations(browser):
    found = collect(browser)
    if os.environ.get("A11Y_REPORT"):
        for role, mode, path, impact, v in found:
            print(f"{impact:9} {role:14} {mode:9} {path:28} {v['id']} x{v['n']} {v['sample'][:1]}")
    # /docs is the bundled third-party Swagger UI: its own widgets (small targets, nested controls, contrast) cannot be
    # changed here, so only the page-level rule we do control is enforced there. /dev/docs is the accessible reference.
    third_party = {"target-size", "nested-interactive", "color-contrast", "scrollable-region-focusable", "aria-allowed-attr", "aria-required-children"}
    bad = [f for f in found if f[3] in ("serious", "critical") and not (f[2] == "/docs" and f[4]["id"] in third_party)]
    assert not bad, "\n".join(f"{r} {m} {p}: {v['id']} ({i}) {v['sample']}" for r, m, p, i, v in bad[:40])
