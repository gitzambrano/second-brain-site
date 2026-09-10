from __future__ import annotations

import contextlib
import http.server
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


@contextlib.contextmanager
def server():
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(ROOT), **kw)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def visible(page, selector: str) -> bool:
    return page.locator(selector).evaluate(
        "el => { const s=getComputedStyle(el),r=el.getBoundingClientRect(); return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && r.height>0; }"
    )


def rect(page, selector: str):
    return page.locator(selector).evaluate(
        "el => {const r=el.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};}"
    )


def overlaps(a, b) -> bool:
    return not (a["right"] <= b["left"] or b["right"] <= a["left"] or a["bottom"] <= b["top"] or b["bottom"] <= a["top"])


with sync_playwright() as p, server() as base:
    browser = p.chromium.launch(headless=True)
    try:
        # Landing mobile: fixed order/visibility and equal external icon geometry.
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(base + "/index.html", wait_until="load")
        brand = rect(page, ".brand-mark")
        theme = rect(page, "#themeToggle")
        assert round(brand["width"]) == round(theme["width"]) == 36
        assert round(brand["height"]) == round(theme["height"]) == 36
        assert not visible(page, ".brand > span:last-child")
        assert not visible(page, ".topnav .nav-link.active")
        assert visible(page, '.topnav a[href="graph.html"]')
        assert visible(page, "#subscribeOpen") and visible(page, "#themeToggle")
        glyph_px = float(page.locator("#themeToggle span").evaluate("el => parseFloat(getComputedStyle(el).fontSize)"))
        assert glyph_px >= 18

        # Dark landing borders: brand, CTA and theme all use the same neutral border token.
        page.evaluate("localStorage.setItem('sb-theme','dark'); location.reload()")
        page.wait_for_load_state("load")
        borders = page.locator(".brand-mark, #subscribeOpen, #themeToggle").evaluate_all(
            "els => els.map(el => getComputedStyle(el).borderTopColor)"
        )
        assert len(set(borders)) == 1, borders
        page.close()

        essays = sorted((ROOT / "essays").glob("*.html"))
        assert essays
        preferred = ROOT / "essays" / "dinamica-analitica-e-acoplamento-fisico-do-modo-dutch-roll.html"
        essay = preferred if preferred.exists() else essays[0]

        # Essay mobile: same chrome, Essays hidden, Assinar retained, read-progress still moves.
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(base + "/essays/" + essay.name, wait_until="load")
        mark = rect(page, ".sb-mark")
        theme = rect(page, "#sbTheme")
        assert round(mark["width"]) == round(theme["width"]) == 36
        assert round(mark["height"]) == round(theme["height"]) == 36
        assert not visible(page, ".sb-nav a:first-child")
        assert visible(page, '.sb-nav a[href="../graph.html"]')
        assert visible(page, "#sbSubscribe") and visible(page, "#sbTheme")
        assert page.locator(".sb-brand").evaluate("el => parseFloat(getComputedStyle(el).fontSize)") == 0
        progress = page.locator("#sbProgressFill")
        assert progress.count() == 1
        before = float(progress.evaluate("el => parseFloat(getComputedStyle(el).width)"))
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight * 0.55)")
        page.wait_for_timeout(120)
        after = float(progress.evaluate("el => parseFloat(getComputedStyle(el).width)"))
        assert after > before, (before, after)
        page.close()

        # A real !note in dark mode must separate from the page surface.
        note_essay = next((x for x in essays if 'class="box callout-note' in x.read_text(encoding="utf-8")), None)
        assert note_essay is not None
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.add_init_script("localStorage.setItem('sb-theme','dark')")
        page.goto(base + "/essays/" + note_essay.name, wait_until="load")
        body_bg = page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor")
        note_bg = page.locator(".box.callout-note").first.evaluate("el => getComputedStyle(el).backgroundColor")
        assert body_bg != note_bg, (body_bg, note_bg)
        page.close()

        # Graph mobile: bottom controls have the requested touch height and do not cover the expandable panel.
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(base + "/graph.html", wait_until="load")
        page.wait_for_timeout(500)
        if not visible(page, "#panel"):
            page.locator("#panel-toggle").click()
            page.wait_for_timeout(100)
        panel = rect(page, "#panel")
        back = rect(page, "#sb-back")
        switch = rect(page, "#sb-map-switch")
        assert back["height"] >= 36
        assert page.locator("#sb-map-switch a").first.evaluate("el => el.getBoundingClientRect().height") >= 36
        assert not overlaps(panel, back), (panel, back)
        assert not overlaps(panel, switch), (panel, switch)

        # Expanded Style/configuration page sits above the floating chrome on mobile.
        page.locator("#btn-style").click()
        page.wait_for_timeout(120)
        modal_z = int(page.locator("#modal").evaluate("el => parseInt(getComputedStyle(el).zIndex || '0', 10)"))
        chrome_z = int(page.locator("#sb-back").evaluate("el => parseInt(getComputedStyle(el).zIndex || '0', 10)"))
        assert modal_z > chrome_z, (modal_z, chrome_z)
        page.close()

        # Desktop keeps the same stacking guarantee for the expandable configuration UI.
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "/graph.html", wait_until="load")
        page.wait_for_timeout(350)
        page.locator("#btn-style").click()
        page.wait_for_timeout(100)
        modal_z = int(page.locator("#modal").evaluate("el => parseInt(getComputedStyle(el).zIndex || '0', 10)"))
        chrome_z = int(page.locator("#sb-back").evaluate("el => parseInt(getComputedStyle(el).zIndex || '0', 10)"))
        assert modal_z > chrome_z
        page.close()
    finally:
        browser.close()

print("custom UI browser validation: PASS")
