from pathlib import Path

path = Path('.github/scripts/validate_ui_polish.py')
text = path.read_text(encoding='utf-8')
old = '''        page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        borders = page.locator(".brand-mark, #subscribeOpen, #themeToggle").evaluate_all(
'''
new = '''        page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        page.wait_for_timeout(250)  # let the 160ms control-border transition settle
        borders = page.locator(".brand-mark, #subscribeOpen, #themeToggle").evaluate_all(
'''
if old not in text:
    raise SystemExit('dark border assertion block not found')
path.write_text(text.replace(old, new), encoding='utf-8')
print('browser assertion now measures settled control borders')
