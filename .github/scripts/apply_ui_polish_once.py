from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def patch_text(text: str, old: str, new: str, *, label: str, count: int = 1) -> str:
    found = text.count(old)
    if found != count:
        raise SystemExit(f"{label}: expected {count} occurrence(s), found {found}: {old[:100]!r}")
    return text.replace(old, new)


def patch_file(rel: str, changes: list[tuple[str, str, int]]) -> None:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    for old, new, count in changes:
        text = patch_text(text, old, new, label=rel, count=count)
    path.write_text(text, encoding="utf-8")


# Landing CSS and CTA.
patch_file(
    "assets/site.css",
    [
        (
            ".brand-mark {\n  width: 31px; height: 31px;\n  display: grid;\n  place-items: center;\n  border: 1px solid color-mix(in srgb, var(--accent) 42%, transparent);\n  border-radius: 9px;",
            ".brand-mark {\n  width: 36px; height: 36px;\n  display: grid;\n  place-items: center;\n  border: 1px solid var(--line);\n  border-radius: 10px;",
            1,
        ),
        (
            "  .nav-link { font-size: 13px; }\n\n  .masthead",
            "  .nav-link { font-size: 13px; }\n  .brand > span:last-child { display: none; }\n  .icon-button > span { font-size: 1.2rem; line-height: 1; }\n\n  .masthead",
            1,
        ),
    ],
)
patch_file(
    "index.html",
    [
        (
            ".subscribe-cta{display:inline-flex;align-items:center;justify-content:center;min-height:34px;padding:0 12px;border:1px solid color-mix(in srgb,var(--accent) 42%,var(--line));border-radius:999px;background:var(--accent-soft);color:var(--accent);font:650 12.5px var(--sans);cursor:pointer;transition:border-color .16s var(--ease),background .16s var(--ease),color .16s var(--ease)}",
            ".subscribe-cta{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:color-mix(in srgb,var(--accent) 13%,var(--panel));color:var(--accent);font:650 12.5px var(--sans);cursor:pointer;transition:border-color .16s var(--ease),background .16s var(--ease),color .16s var(--ease)}",
            1,
        ),
        (
            ".subscribe-cta:hover{border-color:color-mix(in srgb,var(--accent) 72%,var(--line));background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--text-strong)}",
            ".subscribe-cta:hover{border-color:var(--line-strong);background:color-mix(in srgb,var(--accent) 17%,var(--panel));color:var(--text-strong)}",
            1,
        ),
        (
            "@media(max-width:760px){.topnav .nav-link.active{display:none}.subscribe-cta{min-height:32px;padding-inline:10px;font-size:12px}",
            "@media(max-width:760px){.topnav .nav-link.active{display:none}.subscribe-cta{min-height:36px;padding-inline:10px;font-size:12px}",
            1,
        ),
    ],
)

# Update the cache-busting fingerprint exactly as build_site.py does.
site_css = ROOT / "assets" / "site.css"
digest = hashlib.sha256(site_css.read_bytes()).hexdigest()[:8]
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
index, n = re.subn(r"assets/site\.css\?v=[0-9a-f]{8}", f"assets/site.css?v={digest}", index, count=1)
if n != 1:
    raise SystemExit("index.html: site.css fingerprint not found exactly once")
index_path.write_text(index, encoding="utf-8")

# Every public essay is the same generated reader shell; patch that shell, not authored content.
essay_changes = [
    ("  --callout-note:#A2988A;\n", "  --callout-note:#A2988A;\n  --note-bg:color-mix(in srgb,var(--callout-note) 7%,var(--surface2));\n", 1),
    ("  --callout-note:#4A5C77;\n", "  --callout-note:#4A5C77;\n  --note-bg:var(--surface2);\n", 2),
    (".box.callout-note{\n  border:1px solid var(--border);border-radius:3px;\n  background:var(--surface2);\n}", ".box.callout-note{\n  border:1px solid var(--border);border-radius:3px;\n  background:var(--note-bg,var(--surface2));\n}", 1),
    ("body{padding-top:56px;}", "body{padding-top:68px;}", 1),
    ("position:fixed;inset:0 0 auto 0;z-index:60;height:56px;", "position:fixed;inset:0 0 auto 0;z-index:60;height:68px;", 1),
    (".sb-mark{\n  display:grid;place-items:center;width:27px;height:27px;\n  border:1px solid color-mix(in srgb,var(--sb-primary) 42%,transparent);\n  border-radius:8px;color:var(--sb-primary);background:var(--sb-primary-soft);", ".sb-mark{\n  display:grid;place-items:center;width:36px;height:36px;\n  border:1px solid var(--sb-line);\n  border-radius:10px;color:var(--sb-primary);background:var(--sb-primary-soft);", 1),
    ("background:url(\"../assets/icon-32.png\") center / 18px 18px no-repeat, var(--sb-primary-soft);", "background:url(\"../assets/icon-32.png\") center / 20px 20px no-repeat, var(--sb-primary-soft);", 1),
    (".sb-nav{display:flex;align-items:center;gap:16px;}", ".sb-nav{display:flex;align-items:center;gap:20px;}", 1),
    (".sb-nav a{color:var(--sb-muted) !important;font-size:13px;text-decoration:none !important;}", ".sb-nav a{color:var(--sb-muted) !important;font-size:14px;font-weight:500;text-decoration:none !important;}", 1),
    (".sb-nav button{\n  width:32px;height:32px;border:1px solid var(--sb-line);border-radius:9px;", ".sb-nav button{\n  width:36px;height:36px;border:1px solid var(--sb-line);border-radius:10px;", 1),
    (".sb-nav .sb-subscribe{\n  width:auto;height:32px;padding:0 10px;\n  border-color:color-mix(in srgb,var(--sb-primary) 42%,var(--sb-line));border-radius:999px;\n  background:var(--sb-primary-soft);color:var(--sb-primary);font:650 12px/1 Inter,ui-sans-serif,system-ui,sans-serif;\n}", ".sb-nav .sb-subscribe{\n  width:auto;height:36px;padding:0 12px;\n  border-color:var(--sb-line);border-radius:999px;\n  background:color-mix(in srgb,var(--sb-primary) 13%,var(--sb-surface));color:var(--sb-primary);font:650 12.5px/1 Inter,ui-sans-serif,system-ui,sans-serif;\n}", 1),
    ("#sbTheme{border-color:color-mix(in srgb,var(--sb-primary) 42%,var(--sb-line));}", "#sbTheme{border-color:var(--sb-line);}", 1),
    ("position:fixed;top:56px;left:0;right:0;z-index:61;height:2px;background:transparent;", "position:fixed;top:68px;left:0;right:0;z-index:61;height:2px;background:transparent;", 1),
    ("border:1px solid var(--sb-line-strong);border-radius:999px;\n  background:color-mix(in srgb,var(--sb-surface) 96%,transparent);", "border:1px solid var(--sb-line);border-radius:999px;\n  background:color-mix(in srgb,var(--sb-surface) 96%,transparent);", 1),
    ("  .sb-bar{padding-inline:14px;}", "  .sb-bar{height:60px;padding-inline:14px;}\n  body{padding-top:60px;}\n  body > .sb-progress:not(:has(.sb-progress-fill)){top:60px;}", 1),
    ("  .sb-nav{gap:6px;}", "  .sb-nav{gap:8px;}", 1),
    ("  .sb-nav a{font-size:12px;}", "  .sb-nav a{font-size:13px;}", 1),
    ("  .sb-brand{font-size:13px;}", "  .sb-brand{gap:0;font-size:0;}\n  .sb-nav a:first-child{display:none;}", 1),
    ("  .sb-nav button{width:44px;height:44px;}", "  .sb-nav button{width:36px;height:36px;}", 1),
    ("  .sb-subscribe{display:none;}", "  .sb-subscribe{display:inline-flex;}", 1),
    ("  .sb-brand{gap:7px;font-size:0;}", "  .sb-brand{gap:0;font-size:0;}", 1),
    ("  .sb-nav{gap:14px;}", "  .sb-nav{gap:8px;}", 1),
    ("  .sb-nav a{font-size:12.5px;}", "  .sb-nav a{font-size:13px;}", 1),
    ('<span class="sb-mark" aria-hidden="true"></span>Second Brain Atlas</a>', '<span class="sb-mark" aria-hidden="true"></span>Second Brain</a>', 1),
]
essays = sorted((ROOT / "essays").glob("*.html"))
if not essays:
    raise SystemExit("no public essays found")
for path in essays:
    text = path.read_text(encoding="utf-8")
    for old, new, count in essay_changes:
        text = patch_text(text, old, new, label=path.name, count=count)
    path.write_text(text, encoding="utf-8")

# Shared public map chrome in graph and globe.
def patch_map_chrome(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "  /* z-index baixo (8): o cromo"
    at = text.rfind(marker)
    if at < 0:
        raise SystemExit(f"{path.name}: public chrome marker missing")
    core, chrome = text[:at], text[at:]
    for old, new, count in [
        ("    padding: 9px 15px; border-radius: 999px;", "    min-height: 36px; padding: 9px 15px; border-radius: 999px;", 2),
        ("    padding: 9px 13px; border-radius: 999px;", "    min-height: 36px; padding: 9px 13px; border-radius: 999px;", 1),
        ("  #panel { padding-bottom: 56px; }", "  #panel { padding-bottom: 60px; }", 1),
        ("    #panel { bottom: 58px; border-radius: 14px; }", "    #panel { bottom: calc(64px + env(safe-area-inset-bottom)); border-radius: 14px; }", 1),
        ("    #sb-back, #sb-map-switch a, #sb-theme { padding: 7px 11px; font-size: 12px; }", "    #sb-back, #sb-map-switch a, #sb-theme { min-height:36px; padding:8px 12px; font-size:13px; }", 1),
        ("    --edge: #5b6570;", "    --edge: #a7b0ba;", 1),
        ("          styleConfig.colors.edge = theme === 'light' ? '#8a99aa' : '#9aa0a8';\n          applyStyle(styleConfig, { silent: true });", "          styleConfig.colors.edge = theme === 'light' ? '#a7b0ba' : '#858b93';\n          // Migrate only the legacy factory opacity; explicit user choices survive.\n          if (styleConfig.edgeOpacity === 0.35) styleConfig.edgeOpacity = 0.28;\n          applyStyle(styleConfig, { silent: true });", 1),
    ]:
        chrome = patch_text(chrome, old, new, label=path.name + " chrome", count=count)
    path.write_text(core + chrome, encoding="utf-8")


for map_name in ("graph.html", "sphere.html"):
    patch_map_chrome(ROOT / map_name)

# Core graph defaults and label threshold. Patch the generated graph only.
graph_path = ROOT / "graph.html"
graph = graph_path.read_text(encoding="utf-8")
for old, new in [
    ('"edge": "#9aa0a8"', '"edge": "#858b93"'),
    ('"edgeOpacity": 0.35', '"edgeOpacity": 0.28'),
    ('edge: "#9aa0a8"', 'edge: "#858b93"'),
    ('edgeOpacity: 0.35', 'edgeOpacity: 0.28'),
    ("const LABEL_SHOW_AT = 1.55;", "const LABEL_SHOW_AT = 1.40;"),
    ("const LABEL_HIDE_AT = 1.45;", "const LABEL_HIDE_AT = 1.32;"),
]:
    if old not in graph:
        raise SystemExit(f"graph.html: expected generated token missing: {old}")
    graph = graph.replace(old, new)
graph_path.write_text(graph, encoding="utf-8")

# Static deployment invariants.
assert "assets/site.css?v=" + digest in (ROOT / "index.html").read_text(encoding="utf-8")
assert all("id=\"sbProgressFill\"" in p.read_text(encoding="utf-8") for p in essays)
assert all(".sb-nav a:first-child{display:none;}" in p.read_text(encoding="utf-8") for p in essays)
assert "const LABEL_SHOW_AT = 1.40;" in graph
assert "bottom: calc(64px + env(safe-area-inset-bottom))" in graph
print(f"patched {len(essays)} essays; site.css fingerprint={digest}")
