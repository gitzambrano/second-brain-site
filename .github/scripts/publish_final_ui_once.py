from __future__ import annotations

import base64
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "index.html"
GRAPH = ROOT / "graph.html"
SPHERE = ROOT / "sphere.html"
ESSAYS = ROOT / "essays"


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label}: expected {expected} occurrence(s), got {count}")
    return text.replace(old, new)


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"{label}: start marker not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f"{label}: end marker not found")
    if text.find(start_marker, start + len(start_marker)) >= 0:
        raise SystemExit(f"{label}: expected one start marker")
    return text[:start] + replacement + text[end:]


def patch_public_chrome(text: str, label: str) -> str:
    old_links = '''  #sb-map-switch a {
    min-height: 36px; padding: 9px 15px; border-radius: 999px;
    border: 1px solid rgba(255,255,255,.16);
    background: rgba(9,9,9,.88); backdrop-filter: blur(10px);
    color: #e8eef7; font: 600 14px/1 Inter, system-ui, sans-serif;
    text-decoration: none; white-space: nowrap;
  }'''
    new_links = '''  #sb-map-switch a {
    box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center;
    height: 36px; min-height: 36px; padding: 0 15px; border-radius: 999px;
    border: 1px solid rgba(255,255,255,.16);
    background: rgba(9,9,9,.88); backdrop-filter: blur(10px);
    color: #e8eef7; font: 600 14px/1 Inter, system-ui, sans-serif;
    text-decoration: none; white-space: nowrap;
  }'''
    old_theme = '''  #sb-theme {
    min-height: 36px; padding: 9px 13px; border-radius: 999px;
    border: 1px solid rgba(255,255,255,.16);
    background: rgba(9,9,9,.88); backdrop-filter: blur(10px);
    color: #e8eef7; font: 600 14px/1 Inter, system-ui, sans-serif; cursor: pointer;
  }'''
    new_theme = '''  #sb-theme {
    box-sizing: border-box; width: 36px; height: 36px; min-height: 36px; padding: 0;
    display: grid; place-items: center; border-radius: 999px;
    border: 1px solid rgba(255,255,255,.16);
    background: rgba(9,9,9,.88); backdrop-filter: blur(10px);
    color: #e8eef7; font: 600 18px/1 Inter, system-ui, sans-serif; cursor: pointer;
  }'''
    old_mobile = '    #sb-back, #sb-map-switch a, #sb-theme { min-height:36px; padding:8px 12px; font-size:13px; }'
    new_mobile = '    #sb-back, #sb-map-switch a { box-sizing:border-box; height:36px; min-height:36px; padding:0 12px; font-size:13px; }\n    #sb-theme { width:36px; height:36px; min-height:36px; padding:0; font-size:21px; line-height:1; }'
    text = replace_exact(text, old_links, new_links, f"{label} switch controls")
    text = replace_exact(text, old_theme, new_theme, f"{label} theme control")
    text = replace_exact(text, old_mobile, new_mobile, f"{label} mobile chrome")
    return text


def patch_compressed_default_style(text: str, label: str) -> str:
    pattern = re.compile(
        r'(<script id="graph-data" type="application/json" data-encoding="gzip-base64">)(.*?)(</script>)',
        re.S,
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"{label}: compressed graph-data payload not found")
    try:
        raw = gzip.decompress(base64.b64decode(match.group(2).strip())).decode("utf-8")
        payload = json.loads(raw)
    except Exception as exc:
        raise SystemExit(f"{label}: cannot decode graph-data: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label}: graph-data must be an object")
    style = payload.get("defaultStyle")
    if not isinstance(style, dict):
        raise SystemExit(f"{label}: defaultStyle missing; keys={sorted(payload.keys())}")
    colors = style.setdefault("colors", {})
    if not isinstance(colors, dict):
        raise SystemExit(f"{label}: defaultStyle.colors must be an object")
    colors["edge"] = "#858b93"
    style["edgeOpacity"] = 0.28
    encoded_raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(encoded_raw, compresslevel=9, mtime=0)).decode("ascii")
    text = text[: match.start(2)] + encoded + text[match.end(2) :]

    verify = pattern.search(text)
    decoded = json.loads(gzip.decompress(base64.b64decode(verify.group(2))).decode("utf-8"))
    vstyle = decoded["defaultStyle"]
    if vstyle.get("edgeOpacity") != 0.28 or vstyle.get("colors", {}).get("edge") != "#858b93":
        raise SystemExit(f"{label}: compressed style verification failed")
    return text


# Landing CTA only. Prove the library/search/layout controls are byte-identical.
index = INDEX.read_text(encoding="utf-8")
library_marker = '<section class="library shell" id="library">'
if library_marker not in index:
    raise SystemExit("index: library marker missing")
library_suffix = index[index.index(library_marker) :]
index = replace_exact(
    index,
    'background:color-mix(in srgb,var(--accent) 13%,var(--panel));',
    'background:var(--accent-soft);',
    "index subscribe CTA",
)
if index[index.index(library_marker) :] != library_suffix:
    raise SystemExit("index: library section changed unexpectedly")
INDEX.write_text(index, encoding="utf-8")

# Essays: only the CTA token changes; all content and reading-progress markup stay intact.
essay_files = sorted(ESSAYS.glob("*.html"))
if not essay_files:
    raise SystemExit("no public essays found")
changed_essays = 0
for path in essay_files:
    text = path.read_text(encoding="utf-8")
    old = 'background:color-mix(in srgb,var(--sb-primary) 13%,var(--sb-surface));'
    if old not in text:
        raise SystemExit(f"{path.name}: expected stale subscribe CTA token")
    if text.count(old) != 1:
        raise SystemExit(f"{path.name}: stale CTA token count={text.count(old)}")
    before_progress = text.count('id="sbProgressFill"')
    text = text.replace(old, 'background:var(--sb-primary-soft);')
    if text.count('id="sbProgressFill"') != before_progress or before_progress != 1:
        raise SystemExit(f"{path.name}: reading progress marker changed")
    path.write_text(text, encoding="utf-8")
    changed_essays += 1

# Plane graph: project the source changes already validated in the engine.
graph = GRAPH.read_text(encoding="utf-8")
graph, note_removed = re.subn(r'\n<!-- canvas2svg .*?-->\n', '\n', graph, flags=re.S)
if note_removed != 1:
    raise SystemExit(f"graph: expected one obsolete canvas2svg note, got {note_removed}")
graph = replace_exact(
    graph,
    "const LABEL_SHOW_AT = 0.96;\nconst LABEL_HIDE_AT = 0.90;",
    "const LABEL_SHOW_AT = DEVICE_IS_MOBILE ? 0.62 : 0.78;\nconst LABEL_HIDE_AT = DEVICE_IS_MOBILE ? 0.56 : 0.72;",
    "graph label thresholds",
)

png_block = '''let pngExportBusy = false;
const exportPngBtn = document.getElementById("btn-export-png");
exportPngBtn.addEventListener("click", () => {
  if (pngExportBusy) return;
  pngExportBusy = true;
  exportPngBtn.setAttribute("aria-busy", "true");
  requestAnimationFrame(() => {
    canvas.toBlob((blob) => {
      pngExportBusy = false;
      exportPngBtn.removeAttribute("aria-busy");
      if (!blob) {
        alert("Não foi possível gerar o PNG neste navegador.");
        return;
      }
      const url = URL.createObjectURL(blob);
      const stamp = new Date().toISOString().slice(0, 10);
      const a = document.createElement("a");
      a.href = url;
      a.download = `grafo-second-brain-${stamp}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "image/png");
  });
});

'''
graph = replace_between(graph, "const EXPORT_SCALE = 3;", "// ---- Exportar SVG", png_block, "graph PNG export")

svg_block = r'''// ---- Exportar SVG ---------------------------------------------------------
// Gera SVG diretamente, sem dependência externa, no mesmo gesto de clique.
function escapeXml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;"
  }[ch]));
}
function svgNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? String(Math.round(n * 1000) / 1000) : "0";
}
function buildSvgExport() {
  zoomTransform = d3.zoomTransform(canvas);
  const bg = (styleConfig.colors && styleConfig.colors.background) || "#1b1e21";
  const edgeColor = (styleConfig.colors && styleConfig.colors.edge) || "#858b93";
  const [wx0, wy0] = zoomTransform.invert([0, 0]);
  const [wx1, wy1] = zoomTransform.invert([width, height]);
  const pad = 80;
  const inView = n => n && n.x >= wx0 - pad && n.x <= wx1 + pad && n.y >= wy0 - pad && n.y <= wy1 + pad;
  const parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<svg xmlns="http://www.w3.org/2000/svg" width="${svgNumber(width)}" height="${svgNumber(height)}" viewBox="0 0 ${svgNumber(width)} ${svgNumber(height)}" preserveAspectRatio="xMidYMid meet">`,
    `<rect width="100%" height="100%" fill="${escapeXml(bg)}"/>`,
    `<g transform="translate(${svgNumber(zoomTransform.x)} ${svgNumber(zoomTransform.y)}) scale(${svgNumber(zoomTransform.k)})">`,
  ];

  if (styleConfig.edgeVisibility !== "off") {
    data.edges.forEach(e => {
      const s = endpoint(e.source), t = endpoint(e.target);
      if (!s || !t || !isNodeVisible(s) || !isNodeVisible(t)) return;
      if (!inView(s) && !inView(t)) return;
      const opacity = edgeDimmed(e) ? 0.08 : styleConfig.edgeOpacity;
      const dash = e.kind === "reference" ? ' stroke-dasharray="3 3"' : "";
      parts.push(`<line x1="${svgNumber(s.x)}" y1="${svgNumber(s.y)}" x2="${svgNumber(t.x)}" y2="${svgNumber(t.y)}" stroke="${escapeXml(edgeColor)}" stroke-opacity="${svgNumber(opacity)}" stroke-width="1.2" vector-effect="non-scaling-stroke"${dash}/>`);
    });
  }

  data.nodes.forEach(n => {
    if (!isNodeVisible(n) || !inView(n)) return;
    const r = radiusOf(n);
    const opacity = nodeDimmed(n) ? 0.08 : 1;
    const fill = typeColorRaw(n);
    parts.push(`<circle cx="${svgNumber(n.x)}" cy="${svgNumber(n.y)}" r="${svgNumber(r)}" fill="${escapeXml(fill)}" fill-opacity="${svgNumber(opacity)}" stroke="#0b1220" stroke-width="1" vector-effect="non-scaling-stroke"/>`);
  });

  if (labelsShown) {
    const labelColor = getLabelColor();
    data.nodes.forEach(n => {
      if (n.type === "reference" || !isNodeVisible(n) || !inView(n)) return;
      const opacity = nodeDimmed(n) ? 0.08 : (isLightTheme() ? 0.78 : 0.85);
      const y = n.y - (2 + radiusOf(n));
      parts.push(`<text x="${svgNumber(n.x)}" y="${svgNumber(y)}" fill="${escapeXml(labelColor)}" fill-opacity="${svgNumber(opacity)}" font-size="${svgNumber(styleConfig.labelSize)}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" text-anchor="middle">${escapeXml(n.title)}</text>`);
    });
  }

  parts.push("</g></svg>");
  return parts.join(String.fromCharCode(10));
}

function exportSvgFile() {
  const svgString = buildSvgExport();
  const blob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const stamp = new Date().toISOString().slice(0, 10);
  const a = document.createElement("a");
  a.href = url;
  a.download = `grafo-second-brain-${stamp}.svg`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

document.getElementById("btn-export-svg").addEventListener("click", exportSvgFile);

'''
graph = replace_between(graph, "// ---- Exportar SVG", "// Fechar o modal de Estilo", svg_block, "graph SVG export")
graph, css_removed = re.subn(r'\n  #export-svg-popover \{.*?\n  #export-svg-popover p \{[^\n]*\}\n', '\n', graph, flags=re.S)
graph, html_removed = re.subn(r'\n<div id="export-svg-popover">.*?</div>\n', '\n', graph, flags=re.S)
if css_removed != 1 or html_removed != 1:
    raise SystemExit(f"graph legacy SVG cleanup: CSS={css_removed}, HTML={html_removed}")
for obsolete in ("export-svg-popover", "btn-export-svg-completo", "btn-export-svg-simples", "ensureC2S", "EXPORT_SCALE"):
    if obsolete in graph:
        raise SystemExit(f"graph: obsolete token remains: {obsolete}")
graph = patch_public_chrome(graph, "graph")
graph = patch_compressed_default_style(graph, "graph")
GRAPH.write_text(graph, encoding="utf-8")

# Sphere: same public chrome and same restrained edge visual defaults as graph.
sphere = SPHERE.read_text(encoding="utf-8")
sphere = patch_public_chrome(sphere, "sphere")
visible_old_color_count = sphere.count("#9aa0a8")
if visible_old_color_count < 1:
    raise SystemExit("sphere: no visible stale edge color found")
sphere = sphere.replace("#9aa0a8", "#858b93")
if "--edge-opacity: 0.55;" in sphere:
    sphere = sphere.replace("--edge-opacity: 0.55;", "--edge-opacity: 0.28;")
if "edgeOpacity: 0.35" in sphere:
    sphere = sphere.replace("edgeOpacity: 0.35", "edgeOpacity: 0.28")
sphere = patch_compressed_default_style(sphere, "sphere")
if "#9aa0a8" in sphere or "edgeOpacity: 0.35" in sphere or "--edge-opacity: 0.55;" in sphere:
    raise SystemExit("sphere: stale edge visual default remains")
if 'edgeVisibility: "sempre"' not in sphere:
    raise SystemExit("sphere: edgeVisibility behavior changed unexpectedly")
SPHERE.write_text(sphere, encoding="utf-8")

print(f"final public UI projection prepared; essays={changed_essays}; sphereColors={visible_old_color_count}")
