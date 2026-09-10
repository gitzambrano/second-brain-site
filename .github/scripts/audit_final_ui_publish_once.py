from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "visual-audit-final"
OUT.mkdir(exist_ok=True)


def as_uri(name: str) -> str:
    return (ROOT / name).resolve().as_uri()


def assert_no_page_errors(errors: list[str], label: str) -> None:
    if errors:
        raise AssertionError(f"{label} page errors: {errors}")


with sync_playwright() as p:
    browser = p.chromium.launch()

    # Landing — verify CTA/popup plus an untouched library surface.
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(as_uri("index.html"), wait_until="load")
    page.wait_for_selector("#library")
    landing = page.evaluate("""() => {
      const cta = document.querySelector('.subscribe-cta');
      const cs = getComputedStyle(cta);
      const rect = cta.getBoundingClientRect();
      return {
        ctaHeight: rect.height,
        ctaBorder: cs.borderTopColor,
        ctaBackground: cs.backgroundColor,
        hasSearch: !!document.querySelector('.searchbox'),
        hasLayoutControl: !!document.querySelector('[data-layout]'),
        hasDensityControl: !!document.querySelector('[data-density]')
      };
    }""")
    assert abs(landing["ctaHeight"] - 36) < 0.2, landing
    assert landing["hasSearch"] and landing["hasLayoutControl"] and landing["hasDensityControl"], landing
    page.locator(".subscribe-cta").click()
    page.wait_for_selector("dialog.subscribe-dialog[open]")
    popup = page.locator("dialog.subscribe-dialog").inner_text()
    assert "Spam" in popup and "confirme o e-mail" in popup, popup
    assert "Promoções" not in popup and "Não é spam" not in popup, popup
    assert_no_page_errors(errors, "landing")
    page.screenshot(path=str(OUT / "landing-mobile.png"), full_page=True)
    page.close()

    # Representative essay — progress indicator must still react to scrolling.
    essay_path = next(iter(sorted((ROOT / "essays").glob("*.html"))))
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(essay_path.resolve().as_uri(), wait_until="load")
    page.wait_for_selector("#sbProgressFill")
    before = page.locator("#sbProgressFill").evaluate("el => el.getBoundingClientRect().width")
    page.evaluate("window.scrollTo(0, Math.max(600, document.documentElement.scrollHeight * 0.55))")
    page.wait_for_timeout(200)
    after = page.locator("#sbProgressFill").evaluate("el => el.getBoundingClientRect().width")
    assert after > before, {"before": before, "after": after, "essay": essay_path.name}
    essay_nav = page.evaluate("""() => ({
      brandText: document.querySelector('.sb-brand')?.innerText || '',
      hasGraph: Array.from(document.querySelectorAll('.sb-nav a')).some(a => a.textContent.trim() === 'Grafo'),
      essaysVisible: Array.from(document.querySelectorAll('.sb-nav a')).filter(a => a.textContent.trim() === 'Ensaios').some(a => getComputedStyle(a).display !== 'none'),
      themeW: document.querySelector('#sbTheme')?.getBoundingClientRect().width || 0,
      themeH: document.querySelector('#sbTheme')?.getBoundingClientRect().height || 0
    })""")
    assert essay_nav["hasGraph"], essay_nav
    assert not essay_nav["essaysVisible"], essay_nav
    assert abs(essay_nav["themeW"] - 36) < 0.2 and abs(essay_nav["themeH"] - 36) < 0.2, essay_nav
    assert_no_page_errors(errors, "essay")
    page.screenshot(path=str(OUT / "essay-mobile.png"), full_page=False)
    page.close()

    # Plane graph — real mobile chrome + real PNG/SVG downloads.
    page = browser.new_page(viewport={"width": 390, "height": 844}, accept_downloads=True)
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(as_uri("graph.html"), wait_until="load")
    page.wait_for_selector("#graph")
    page.wait_for_function("document.querySelectorAll('#sb-map-switch a').length === 2 && !!document.querySelector('#sb-theme')")
    page.wait_for_timeout(450)
    controls = page.evaluate("""() => {
      const els = document.querySelectorAll('#sb-map-switch a');
      const box = el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return {text:el.textContent.trim(), w:r.width, h:r.height, display:s.display, align:s.alignItems, justify:s.justifyContent, font:s.fontSize};
      };
      return {a:box(els[0]), b:box(els[1]), theme:box(document.querySelector('#sb-theme'))};
    }""")
    assert controls["a"]["text"] == "Grafo" and controls["b"]["text"] == "Globo", controls
    for key in ("a", "b"):
        c = controls[key]
        assert abs(c["h"] - 36) < 0.2 and c["display"] == "flex", (key, c)
        assert c["align"] == "center" and c["justify"] == "center", (key, c)
    assert abs(controls["theme"]["w"] - 36) < 0.2 and abs(controls["theme"]["h"] - 36) < 0.2, controls
    assert controls["theme"]["font"] == "21px", controls

    panel = page.locator("#panel")
    if panel.evaluate("el => el.classList.contains('collapsed')"):
        page.locator("#panel-toggle").click()
    page.wait_for_function("!document.querySelector('#panel').classList.contains('collapsed')")

    png_button = page.locator("#btn-export-png")
    png_button.scroll_into_view_if_needed()
    with page.expect_download(timeout=10000) as info:
        png_button.click()
    png_path = OUT / "graph-export.png"
    info.value.save_as(str(png_path))
    assert png_path.stat().st_size > 1000, png_path.stat().st_size

    svg_button = page.locator("#btn-export-svg")
    svg_button.scroll_into_view_if_needed()
    with page.expect_download(timeout=10000) as info:
        svg_button.click()
    svg_path = OUT / "graph-export.svg"
    info.value.save_as(str(svg_path))
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    assert root.tag.endswith("svg")
    assert any(el.tag.endswith("circle") for el in root.iter())
    assert any(el.tag.endswith("line") for el in root.iter())
    assert_no_page_errors(errors, "graph")
    page.locator("#sb-map-switch").screenshot(path=str(OUT / "graph-mobile-controls.png"))
    page.close()

    # Sphere — same public chrome and no runtime errors; retain globe behavior.
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(as_uri("sphere.html"), wait_until="load")
    page.wait_for_selector("#graph")
    page.wait_for_function("document.querySelectorAll('#sb-map-switch a').length === 2 && !!document.querySelector('#sb-theme')")
    page.wait_for_timeout(450)
    sphere = page.evaluate("""() => {
      const els = document.querySelectorAll('#sb-map-switch a');
      const box = el => { const r=el.getBoundingClientRect(), s=getComputedStyle(el); return {text:el.textContent.trim(),w:r.width,h:r.height,display:s.display,align:s.alignItems,justify:s.justifyContent,font:s.fontSize}; };
      return {a:box(els[0]),b:box(els[1]),theme:box(document.querySelector('#sb-theme')),canvas:document.querySelector('#graph').getBoundingClientRect().toJSON()};
    }""")
    assert sphere["a"]["text"] == "Grafo" and sphere["b"]["text"] == "Globo", sphere
    for key in ("a", "b"):
        c = sphere[key]
        assert abs(c["h"] - 36) < 0.2 and c["display"] == "flex", (key, c)
        assert c["align"] == "center" and c["justify"] == "center", (key, c)
    assert abs(sphere["theme"]["w"] - 36) < 0.2 and abs(sphere["theme"]["h"] - 36) < 0.2, sphere
    assert sphere["theme"]["font"] == "21px", sphere
    assert sphere["canvas"]["width"] >= 389 and sphere["canvas"]["height"] >= 843, sphere["canvas"]
    assert_no_page_errors(errors, "sphere")
    page.locator("#sb-map-switch").screenshot(path=str(OUT / "sphere-mobile-controls.png"))
    page.close()

    browser.close()

print("final browser audit PASS")
