from pathlib import Path

path = Path('.github/scripts/apply_ui_polish_once.py')
text = path.read_text(encoding='utf-8')
old = r'''sub_once_or_done(r'("edge"\s*:\s*)"#9aa0a8"', r'\1"#858b93"', '"edge": "#858b93"', "default edge color")
sub_once_or_done(r'("edgeOpacity"\s*:\s*)0\.35', r'\g<1>0.28', '"edgeOpacity": 0.28', "default edge opacity")
sub_once_or_done(r'(reference:\s*"#8a8f96",\s*edge:\s*)"#9aa0a8"', r'\1"#858b93"', 'edge: "#858b93"', "factory edge color")
sub_once_or_done(r'(edgeOpacity:\s*)0\.35', r'\g<1>0.28', 'edgeOpacity: 0.28', "factory edge opacity")
graph = replace_exact(graph, "const LABEL_SHOW_AT = 1.55;", "const LABEL_SHOW_AT = 1.40;", label="graph labels show", count=1)
graph = replace_exact(graph, "const LABEL_HIDE_AT = 1.45;", "const LABEL_HIDE_AT = 1.32;", label="graph labels hide", count=1)
graph = replace_exact(graph, "    --edge: #9aa0a8;", "    --edge: #858b93;", label="graph css edge", count=1)
'''
new = r'''# Generated graph formatting differs slightly across renderer revisions.
# Replace the legacy visual values wherever they occur, then assert the
# behavior-level tokens below instead of depending on JSON whitespace.
graph = graph.replace("#9aa0a8", "#858b93")
graph = re.sub(r'("edgeOpacity"\s*:\s*)0\.35', r'\g<1>0.28', graph)
graph = re.sub(r'(?<!")\bedgeOpacity\s*:\s*0\.35', 'edgeOpacity: 0.28', graph)
graph = graph.replace("--edge-opacity: 0.55;", "--edge-opacity: 0.28;")
graph = replace_exact(graph, "const LABEL_SHOW_AT = 1.55;", "const LABEL_SHOW_AT = 1.40;", label="graph labels show", count=1)
graph = replace_exact(graph, "const LABEL_HIDE_AT = 1.45;", "const LABEL_HIDE_AT = 1.32;", label="graph labels hide", count=1)
'''
if old not in text:
    raise SystemExit('graph patch block not found')
text = text.replace(old, new)
text = text.replace("assert '\"edgeOpacity\": 0.28' in graph", "assert 'edgeOpacity: 0.28' in graph or '\"edgeOpacity\": 0.28' in graph\nassert '#9aa0a8' not in graph")
path.write_text(text, encoding='utf-8')
print('graph projection patch made format-tolerant')
