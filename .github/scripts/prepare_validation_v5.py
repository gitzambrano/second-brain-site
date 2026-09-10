from pathlib import Path

path = Path('.github/scripts/validate_ui_polish.py')
text = path.read_text(encoding='utf-8')
old = '''modal_z = int(page.locator("#modal").evaluate("el => parseInt(getComputedStyle(el).zIndex || '0', 10)"))'''
new = '''modal_z = int(page.locator("#modal").evaluate("el => { let n=el; while(n){ const z=getComputedStyle(n).zIndex; if(z && z !== 'auto'){ const v=parseInt(z,10); if(Number.isFinite(v)) return v; } n=n.parentElement; } return 0; }"))'''
count = text.count(old)
if count != 2:
    raise SystemExit(f'expected two modal z-index probes, found {count}')
path.write_text(text.replace(old, new), encoding='utf-8')
print('modal stacking audit now follows the effective stacking ancestor')
