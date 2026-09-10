from pathlib import Path

p = Path('.github/scripts/apply_ui_polish_once.py')
text = p.read_text(encoding='utf-8')
old = '''for old, new in [
    ('"edge": "#9aa0a8"', '"edge": "#858b93"'),
    ('"edgeOpacity": 0.35', '"edgeOpacity": 0.28'),
    ('edge: "#9aa0a8"', 'edge: "#858b93"'),
    ('edgeOpacity: 0.35', 'edgeOpacity: 0.28'),
    ("const LABEL_SHOW_AT = 1.55;", "const LABEL_SHOW_AT = 1.40;"),
    ("const LABEL_HIDE_AT = 1.45;", "const LABEL_HIDE_AT = 1.32;"),
]:'''
new = '''for old, new in [
    ("--edge: #9aa0a8;", "--edge: #858b93;"),
    ("--edge-opacity: 0.55;", "--edge-opacity: 0.28;"),
    ('edge: "#9aa0a8"', 'edge: "#858b93"'),
    ('edgeOpacity: 0.35', 'edgeOpacity: 0.28'),
    ("const LABEL_SHOW_AT = 1.55;", "const LABEL_SHOW_AT = 1.40;"),
    ("const LABEL_HIDE_AT = 1.45;", "const LABEL_HIDE_AT = 1.32;"),
]:'''
if text.count(old) != 1:
    raise SystemExit('graph patch block not found exactly once')
p.write_text(text.replace(old, new), encoding='utf-8')
print('site polish runner corrected for generated graph syntax')
