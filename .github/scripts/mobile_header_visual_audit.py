from __future__ import annotations

import contextlib
import http.server
import json
import socketserver
import threading
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "visual-audit"
OUT.mkdir(exist_ok=True)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


@contextlib.contextmanager
def server():
    handler = lambda *a, **kw: Quiet(*a, directory=str(ROOT), **kw)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def rects(page, selectors):
    out = {}
    for name, selector in selectors.items():
        out[name] = page.locator(selector).evaluate(
            "el => {const r=el.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}}"
        )
    return out


def assert_rects_equal(a, b, names):
    for name in names:
        for key in ("left", "top", "right", "bottom", "width", "height"):
            if abs(a[name][key] - b[name][key]) > 0.01:
                raise AssertionError((name, key, a[name][key], b[name][key]))


essay = ROOT / "essays" / "dinamica-analitica-e-acoplamento-fisico-do-modo-dutch-roll.html"
if not essay.exists():
    essay = sorted((ROOT / "essays").glob("*.html"))[0]

with sync_playwright() as p, server() as base:
    browser = p.chromium.launch(headless=True)
    try:
        home = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        home.goto(base + "/index.html", wait_until="load")
        home.evaluate("localStorage.setItem('sb-theme','light'); location.reload()")
        home.wait_for_load_state("load")
        home_rect = rects(home, {
            "header": ".topbar",
            "brand": ".brand-mark",
            "graph": '.topnav a[href="graph.html"]',
            "subscribe": "#subscribeOpen",
            "theme": "#themeToggle",
        })
        home.locator(".topbar").screenshot(path=str(OUT / "home-mobile-header.png"))

        essay_page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        essay_page.goto(base + "/essays/" + essay.name, wait_until="load")
        essay_page.evaluate("localStorage.setItem('sb-theme','light'); location.reload()")
        essay_page.wait_for_load_state("load")
        essay_rect = rects(essay_page, {
            "header": ".sb-bar",
            "brand": ".sb-mark",
            "graph": '.sb-nav a[href="../graph.html"]',
            "subscribe": "#sbSubscribe",
            "theme": "#sbTheme",
        })
        essay_page.locator(".sb-bar").screenshot(path=str(OUT / "essay-mobile-header.png"))

        assert_rects_equal(home_rect, essay_rect, ("header", "brand", "graph", "subscribe", "theme"))
        assert round(home_rect["subscribe"]["height"]) == 36
        assert round(essay_rect["subscribe"]["height"]) == 36

        # The theme glyph must occupy a centered 36x36 grid inside the button.
        glyph = essay_page.locator("#sbTheme > span").evaluate(
            "el => {const r=el.getBoundingClientRect(),p=el.parentElement.getBoundingClientRect();return {w:r.width,h:r.height,cx:r.left+r.width/2-p.left-p.width/2,cy:r.top+r.height/2-p.top-p.height/2,font:parseFloat(getComputedStyle(el).fontSize)}}"
        )
        assert abs(glyph["cx"]) < 0.01 and abs(glyph["cy"]) < 0.01, glyph
        assert glyph["font"] == 21, glyph

        # Reading progress remains functional.
        progress = essay_page.locator("#sbProgressFill")
        assert progress.count() == 1
        before = float(progress.evaluate("el => parseFloat(getComputedStyle(el).width)"))
        essay_page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight * 0.55)")
        essay_page.wait_for_timeout(120)
        after = float(progress.evaluate("el => parseFloat(getComputedStyle(el).width)"))
        assert after > before, (before, after)

        home.close()
        essay_page.close()
    finally:
        browser.close()

home_img = Image.open(OUT / "home-mobile-header.png").convert("RGB")
essay_img = Image.open(OUT / "essay-mobile-header.png").convert("RGB")
assert home_img.size == essay_img.size == (362, 60), (home_img.size, essay_img.size)
diff = ImageChops.difference(home_img, essay_img)
diff.save(OUT / "mobile-header-diff.png")
different = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0))
# Identical geometry is mandatory. A handful of anti-aliasing pixels is accepted
# because the two pages have separate font-loading histories in Chromium.
assert different <= 20, f"header screenshots differ in {different} pixels"

source = (ROOT / "graph.html").read_text(encoding="utf-8")
assert "const LABEL_SHOW_AT = 0.96;" in source
assert "const LABEL_HIDE_AT = 0.90;" in source

report = {"viewport": [390, 844], "home": home_rect, "essay": essay_rect, "glyph": glyph, "different_header_pixels": different}
(OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
print("visual mobile header audit: PASS")
