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
AUDIT = ROOT / "visual-audit"
AUDIT.mkdir(exist_ok=True)
ESSAY = ROOT / "essays" / "dinamica-analitica-e-acoplamento-fisico-do-modo-dutch-roll.html"


def replace_text(path: Path, old: str, new: str, required: bool = True) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if required:
            raise SystemExit(f"pattern not found in {path}: {old[:100]!r}")
        return False
    path.write_text(text.replace(old, new), encoding="utf-8")
    return True


def patch_essay(path: Path) -> None:
    pairs = [
        ("--sb-text:#172235;", "--sb-text:#0a1525;"),
        ("--sb-muted:#607087;", "--sb-muted:#5d6c81;"),
        ("--sb-line:rgba(23,34,53,.14);", "--sb-line:rgba(23,34,53,.12);"),
        ("--sb-line-strong:rgba(23,34,53,.26);", "--sb-line-strong:rgba(23,34,53,.24);"),
        ("--sb-text:#f0ede7;", "--sb-text:#ffffff;"),
        ("--sb-muted:#aaa39a;", "--sb-muted:#a6a6a6;"),
        ("--sb-line:rgba(240,237,231,.14);", "--sb-line:rgba(255,255,255,.11);"),
        ("--sb-line-strong:rgba(240,237,231,.25);", "--sb-line-strong:rgba(255,255,255,.22);"),
        ("display:inline-flex;align-items:center;gap:10px;", "display:inline-flex;align-items:center;gap:11px;"),
        ('<a href="../index.html">Essays</a>', '<a class="active" href="../index.html">Ensaios</a>'),
        ('<button type="button" id="sbTheme" aria-label="Alternar tema" aria-pressed="false">◐</button>', '<button type="button" id="sbTheme" aria-label="Alternar tema" aria-pressed="false"><span aria-hidden="true">◐</span></button>'),
    ]
    for old, new in pairs:
        replace_text(path, old, new)
    replace_text(path,
""".sb-bar{
  position:fixed;inset:0 0 auto 0;z-index:60;height:68px;
  display:flex;align-items:center;justify-content:space-between;gap:16px;
  padding:0 clamp(16px,4vw,40px);
  border-bottom:1px solid var(--sb-line);
  background:color-mix(in srgb,var(--sb-bg) 90%,transparent);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,\"Segoe UI\",sans-serif;
}""",
""".sb-bar{
  position:fixed;top:0;left:50%;transform:translateX(-50%);z-index:60;
  width:min(1120px,calc(100% - 48px));height:68px;
  display:flex;align-items:center;justify-content:space-between;gap:16px;
  padding:0;
  border-bottom:1px solid var(--sb-line);
  background:color-mix(in srgb,var(--sb-bg) 86%,transparent);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,\"Segoe UI\",sans-serif;
}""")
    replace_text(path,
""".sb-nav button{
  width:36px;height:36px;border:1px solid var(--sb-line);border-radius:10px;
  background:transparent;color:var(--sb-primary);cursor:pointer;
}
.sb-nav button:hover{border-color:var(--sb-line-strong);}""",
""".sb-nav button{
  width:36px;height:36px;display:grid;place-items:center;font:inherit;
  border:1px solid var(--sb-line);border-radius:10px;
  background:transparent;color:var(--sb-primary);cursor:pointer;
  transition:border-color .16s cubic-bezier(.22,.61,.36,1);
}
.sb-nav button:hover{border-color:color-mix(in srgb,var(--sb-primary) 55%,var(--sb-line));}""")
    replace_text(path,
""".sb-nav .sb-subscribe{
  width:auto;height:36px;padding:0 12px;
  border-color:var(--sb-line);border-radius:999px;
  background:color-mix(in srgb,var(--sb-primary) 13%,var(--sb-surface));color:var(--sb-primary);font:650 12.5px/1 Inter,ui-sans-serif,system-ui,sans-serif;
}""",
""".sb-nav .sb-subscribe{
  width:auto;height:36px;min-height:36px;padding:0 12px;
  display:inline-flex;align-items:center;justify-content:center;
  border-color:var(--sb-line);border-radius:999px;
  background:color-mix(in srgb,var(--sb-primary) 13%,var(--sb-surface));color:var(--sb-primary);
  font:650 12.5px Inter,ui-sans-serif,system-ui,-apple-system,\"Segoe UI\",sans-serif;
}""")
    replace_text(path,
"""@media(max-width:720px){
  .sb-bar{height:60px;padding-inline:14px;}
  body{padding-top:60px;}
  body > .sb-progress:not(:has(.sb-progress-fill)){top:60px;}
  .sb-nav{gap:8px;}
  .sb-nav a{font-size:13px;}
  .sb-brand{gap:0;font-size:0;}
  .sb-nav a:first-child{display:none;}
  .sb-nav button{width:36px;height:36px;}
  .sb-nav #sbTheme{font-size:1.25rem;}
  .sb-subscribe{display:inline-flex;}""",
"""@media(max-width:720px){
  .sb-bar{width:min(1120px,calc(100% - 28px));height:60px;padding:0;}
  body{padding-top:60px;}
  body > .sb-progress:not(:has(.sb-progress-fill)){top:60px;}
  .sb-nav{gap:14px;}
  .sb-nav a{font-size:13px;}
  .sb-brand{gap:0;font-size:0;}
  .sb-nav a:first-child{display:none;}
  .sb-nav button{width:36px;height:36px;}
  .sb-nav #sbTheme > span{display:block;font-size:1.28rem;line-height:1;}
  .sb-nav .sb-subscribe{height:36px;min-height:36px;padding-inline:10px;font-size:12px;line-height:normal;}
  .sb-subscribe{display:inline-flex;}""")
    replace_text(path, ".sb-nav{gap:8px;}\n  .sb-nav a{font-size:13px;}\n}", ".sb-nav{gap:14px;}\n  .sb-nav a{font-size:13px;}\n}")
    # Active state on desktop matches the landing page.
    replace_text(path, ".sb-nav a:hover{color:var(--sb-primary) !important;}", ".sb-nav a:hover{color:var(--sb-primary) !important;}\n.sb-nav a.active{color:var(--sb-primary) !important;}")


def apply_patch() -> None:
    replace_text(ROOT / "assets/site.css", ".icon-button > span { font-size: 1.2rem; line-height: 1; }", ".icon-button > span { font-size: 1.28rem; line-height: 1; }")
    for essay in sorted((ROOT / "essays").glob("*.html")):
        patch_essay(essay)
    replace_text(ROOT / "graph.html", "const LABEL_SHOW_AT = 1.40;", "const LABEL_SHOW_AT = 1.16;")
    replace_text(ROOT / "graph.html", "const LABEL_HIDE_AT = 1.32;", "const LABEL_HIDE_AT = 1.10;")


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
        httpd.shutdown(); httpd.server_close()


def set_theme(page, theme: str):
    page.add_init_script(f"localStorage.setItem('sb-theme','{theme}')")


def capture(prefix: str) -> dict:
    measurements = {}
    with sync_playwright() as p, server() as base:
        browser = p.chromium.launch(headless=True)
        try:
            for theme in ("light", "dark"):
                # Home
                page = browser.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
                set_theme(page, theme)
                page.goto(base + "/index.html", wait_until="load")
                page.evaluate("document.fonts && document.fonts.ready")
                page.wait_for_timeout(250)
                page.screenshot(path=str(AUDIT / f"{prefix}-home-{theme}.png"), full_page=False)
                measurements[f"{prefix}-home-{theme}"] = page.locator("header.topbar").evaluate("el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}")
                page.close()

                # Essay
                page = browser.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
                set_theme(page, theme)
                page.goto(base + "/essays/" + ESSAY.name, wait_until="load")
                page.evaluate("document.fonts && document.fonts.ready")
                page.wait_for_timeout(250)
                page.screenshot(path=str(AUDIT / f"{prefix}-essay-{theme}.png"), full_page=False)
                measurements[f"{prefix}-essay-{theme}"] = page.locator("header.sb-bar").evaluate("el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}")
                if prefix == "after":
                    # Numeric geometry supports the screenshot review; it does not replace it.
                    selectors = [".sb-mark", '.sb-nav a[href="../graph.html"]', "#sbSubscribe", "#sbTheme"]
                    measurements["essay-controls"] = {s: page.locator(s).evaluate("el=>{const r=el.getBoundingClientRect(),cs=getComputedStyle(el);return {x:r.x,y:r.y,w:r.width,h:r.height,font:cs.fontSize,line:cs.lineHeight}}") for s in selectors}
                    glyph = page.locator("#sbTheme > span").evaluate("el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}")
                    button = page.locator("#sbTheme").evaluate("el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}")
                    measurements["theme-glyph"] = {"glyph":glyph,"button":button}
                page.close()

            if prefix == "after":
                page = browser.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
                page.goto(base + "/graph.html", wait_until="load")
                page.wait_for_timeout(650)
                page.screenshot(path=str(AUDIT / "after-graph-default.png"), full_page=False)
                # Exercise the exact new label threshold and capture it.
                page.evaluate("window.dispatchEvent(new WheelEvent('wheel',{deltaY:-220,clientX:195,clientY:380,bubbles:true,cancelable:true}))")
                page.wait_for_timeout(350)
                page.screenshot(path=str(AUDIT / "after-graph-small-zoom.png"), full_page=False)
                page.close()
        finally:
            browser.close()
    return measurements


def compare_headers(theme: str) -> dict:
    home = Image.open(AUDIT / f"after-home-{theme}.png").convert("RGB").crop((0,0,390,60))
    essay = Image.open(AUDIT / f"after-essay-{theme}.png").convert("RGB").crop((0,0,390,60))
    diff = ImageChops.difference(home, essay)
    diff.save(AUDIT / f"after-header-diff-{theme}.png")
    hist = diff.histogram()
    changed = sum(v for i,v in enumerate(hist) if (i % 256) != 0)
    bbox = diff.getbbox()
    return {"changed_channel_samples":changed,"bbox":bbox}


before = capture("before")
apply_patch()
after = capture("after")
report = {"before":before,"after":after,"diff_light":compare_headers("light"),"diff_dark":compare_headers("dark")}
(AUDIT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

# The canonical mobile bars must occupy the same box, and controls must be sane.
for theme in ("light","dark"):
    assert after[f"after-home-{theme}"] == after[f"after-essay-{theme}"], report
controls = after["essay-controls"]
assert controls["#sbSubscribe"]["h"] == 36
assert controls["#sbSubscribe"]["w"] < 80
assert float(controls["#sbSubscribe"]["font"].replace("px","")) <= 12.1
assert controls["#sbTheme"]["w"] == controls[".sb-mark"]["w"] == 36
# Exact centering within half a pixel.
g = after["theme-glyph"]["glyph"]; b = after["theme-glyph"]["button"]
assert abs((g["x"] + g["w"]/2) - (b["x"] + b["w"]/2)) <= 0.5
assert abs((g["y"] + g["h"]/2) - (b["y"] + b["h"]/2)) <= 0.5

print(json.dumps(report, indent=2))
