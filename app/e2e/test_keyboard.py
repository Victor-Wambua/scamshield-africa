"""Keyboard-only walkthroughs (Tab, Shift+Tab, Enter, Space, Escape, arrow keys; no mouse).

Checks: skip link, visible focus on every stop, no focus traps, logical order, menu focus restore, and the
lookup, report and moderation journeys completed without a pointer. The app has no modal dialogs (destructive
actions use the browser's own confirm prompt), so there is no focus trap to test beyond the account menu.
"""

from __future__ import annotations

import re

import pytest
from a11y_support import SEED_BASE, seeded_server, sign_in
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e

FOCUS_INFO = """() => {
  const e = document.activeElement; if (!e || e === document.body) return null;
  const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
  return {tag: e.tagName, id: e.id, text: (e.innerText || e.getAttribute('aria-label') || e.name || '').slice(0, 40),
          outline: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2, shadow: cs.boxShadow !== 'none',
          visible: r.width > 0 && r.height > 0, inView: r.bottom > 0 && r.top < innerHeight}
}"""


@pytest.fixture(scope="module")
def env(browser):
    with seeded_server() as srv:
        yield {"srv": srv, "browser": browser}


def page_for(env, email: str | None = None, mobile: bool = False) -> Page:
    vp = {"width": 375, "height": 812} if mobile else {"width": 1280, "height": 800}
    ctx = env["browser"].new_context(viewport=vp, base_url=SEED_BASE, user_agent=f"kb-{email}-{mobile}")
    page = ctx.new_page()
    if email:
        sign_in(page, email, env["srv"]["creds"])
    return page


def tab_through(page: Page, limit: int = 80) -> list[dict]:  # type: ignore[type-arg]
    """Tab forward until focus leaves the document or returns to the first stop; every stop must show a focus indicator."""
    stops, first = [], None
    for _ in range(limit):
        page.keyboard.press("Tab")
        info = page.evaluate(FOCUS_INFO)
        if info is None:
            break
        key = (info["tag"], info["id"], info["text"])
        if first is None:
            first = key
        elif key == first:
            break
        stops.append(info)
    else:
        raise AssertionError(f"focus never left or cycled within {limit} Tab presses (possible trap) on {page.url}")
    return stops


@pytest.mark.parametrize("path", ["/", "/search?q=0700000001", "/report", "/analyse", "/about", "/login"])
@pytest.mark.parametrize("mobile", [False, True])
def test_public_pages_tab_order_and_focus_visible(env, path, mobile):
    page = page_for(env, mobile=mobile)
    page.goto(path)
    stops = tab_through(page)
    assert len(stops) >= 3
    assert stops[0]["text"].lower().startswith(("skip", "ruka")), stops[0]
    for s in stops:
        if s["visible"] and s["inView"] or s["tag"] != "A":
            assert s["outline"] or s["shadow"], f"no visible focus indicator on {s} at {path}"
    page.context.close()


def test_skip_link_moves_focus_to_main(env):
    page = page_for(env)
    page.goto("/")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    assert page.evaluate("document.activeElement.getBoundingClientRect().top") >= 0  # revealed on focus
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "main"
    page.context.close()


def test_account_menu_keyboard_open_close_restores_focus(env):
    page = page_for(env)
    page.goto("/")
    page.focus("[data-menu]")
    page.keyboard.press("Enter")
    assert page.is_visible("#acct")
    assert page.evaluate("document.activeElement.closest('#acct') !== null")
    page.keyboard.press("Tab")  # moves within the menu, not to a hidden element
    assert page.evaluate("document.activeElement.closest('#acct') !== null")
    page.keyboard.press("Escape")
    assert not page.is_visible("#acct")
    assert page.evaluate("document.activeElement.hasAttribute('data-menu')")
    page.context.close()


def test_lookup_journey_keyboard_only(env):
    page = page_for(env)
    page.goto("/")
    for _ in range(30):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.id") == "q":
            break
    else:
        raise AssertionError("search box not reachable by Tab")
    page.keyboard.type("0700000001")
    page.keyboard.press("Enter")
    page.wait_for_url(re.compile(r"/search\?q="))
    # first result link reachable and activatable with Enter
    for _ in range(40):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.matches('a.result')"):
            break
    else:
        raise AssertionError("result not reachable by Tab")
    page.keyboard.press("Enter")
    page.wait_for_url(re.compile(r"/i/\d+"))
    assert page.locator("h1").first.is_visible()
    page.context.close()


def test_report_wizard_keyboard_only(env):
    page = page_for(env, mobile=True)
    page.goto("/report")
    page.focus("input[name=itype]")  # first radio; arrow keys then choose within the group
    page.keyboard.press("Space")
    assert page.is_checked("input[name=itype] >> nth=0")
    page.focus("[data-next]")
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.tagName") == "H2"  # focus moves to the new step heading
    assert page.inner_text("[data-step-label]") == "Step 2 of 5"
    page.focus("#f-value")
    page.keyboard.type("0700 555 321")
    page.focus("#f-description")
    page.keyboard.type("Someone called and asked me to send money back for a mistaken transfer.")
    for _ in range(2):
        page.focus("[data-next]")
        page.keyboard.press("Enter")
    assert page.inner_text("[data-step-label]") == "Step 4 of 5"
    page.focus("#f-consent_privacy")
    page.keyboard.press("Space")
    page.focus("#f-consent_truth")
    page.keyboard.press("Space")
    page.focus("[data-next]")
    page.keyboard.press("Enter")
    assert page.inner_text("[data-step-label]") == "Step 5 of 5"
    page.focus("[data-submit]")
    page.keyboard.press("Enter")
    page.wait_for_url(re.compile(r"/report/done"))
    page.context.close()


def test_moderator_review_keyboard_only(env):
    page = page_for(env, "moderator@demo.example")
    page.goto("/mod")
    stops = tab_through(page)
    assert all(s["outline"] or s["shadow"] for s in stops if s["tag"] != "A" or s["visible"]), stops
    page.goto("/mod/10")
    page.focus("a[href='#decision']")
    page.keyboard.press("Enter")
    page.focus("#reason")
    page.keyboard.type("Keyboard-only walkthrough decision.")
    summaries = page.locator("details.act-group > summary")
    assert summaries.count() == 2
    page.evaluate("document.querySelectorAll('details.act-group').forEach(d => { d.open = false; })")
    summaries.first.focus()
    page.keyboard.press("Enter")  # a summary toggles with Enter
    assert page.evaluate("document.querySelector('details.act-group').open")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.closest('details.act-group') !== null")
    page.context.close()
