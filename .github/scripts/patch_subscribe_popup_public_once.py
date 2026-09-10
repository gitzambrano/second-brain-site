from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, got {count}")
    return text.replace(old, new, 1)


# Landing.
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
index = replace_one(index,
    '.subscribe-dialog-note{margin:-4px 24px 24px;padding:0;color:var(--muted);font-size:11.5px;line-height:1.5}',
    '.subscribe-dialog-note{margin:-4px 24px 24px;padding:0;color:var(--muted);font-size:13.5px;line-height:1.55}',
    'landing note size')
index = replace_one(index,
    '.subscribe-embed .formkit-input{width:100%!important;min-height:44px!important;margin:0!important;padding:0 13px!important;',
    '.subscribe-embed .formkit-input{box-sizing:border-box!important;width:100%!important;min-height:44px!important;margin:0!important;padding:0 13px!important;',
    'landing input sizing')
index = replace_one(index,
'''  <div class="subscribe-dialog-head">
    <p class="subscribe-dialog-eyebrow">Ensaios · Second Brain</p>
    <h2 id="subscribeTitle">Novos ensaios por e-mail.</h2>
    <p class="subscribe-dialog-lede">Só quando houver publicação nova.</p>
    <form method="dialog"><button class="subscribe-close" type="submit" aria-label="Fechar">×</button></form>
  </div>''',
'''  <div class="subscribe-dialog-head">
    <h2 id="subscribeTitle">Receba novos ensaios por email.</h2>
    <form method="dialog"><button class="subscribe-close" type="submit" aria-label="Fechar">×</button></form>
  </div>''',
    'landing title block')
index = replace_one(index,
    '<p class="subscribe-dialog-note"><strong>Importante:</strong> confira também a pasta de <strong>Spam</strong> e confirme o e-mail.</p>',
    '<p class="subscribe-dialog-note"><u>Confirme</u> o e-mail recebido. Verifique a <u>caixa de spam</u>. Marque o email como confiável. Você não receberá mensagens de spam.</p>',
    'landing note')
index_path.write_text(index, encoding="utf-8")

# Essays already contain the source CSS/markup inline; patch each public page only.
essays = sorted((ROOT / "essays").glob("*.html"))
if not essays:
    raise SystemExit('no public essays found')
for path in essays:
    text = path.read_text(encoding="utf-8")
    text = replace_one(text,
        '.sb-subscribe-note{margin:-4px 24px 24px!important;padding:0;color:var(--sb-muted)!important;font:11.5px/1.5 Inter,ui-sans-serif,system-ui,sans-serif!important;}',
        '.sb-subscribe-note{margin:-4px 24px 24px!important;padding:0;color:var(--sb-muted)!important;font:13.5px/1.55 Inter,ui-sans-serif,system-ui,sans-serif!important;}',
        f'{path.name} note size')
    text = replace_one(text,
        '.sb-subscribe-embed .formkit-input{width:100%!important;min-height:44px!important;margin:0!important;padding:0 13px!important;',
        '.sb-subscribe-embed .formkit-input{box-sizing:border-box!important;width:100%!important;min-height:44px!important;margin:0!important;padding:0 13px!important;',
        f'{path.name} input sizing')
    text = replace_one(text,
'''  <div class="sb-subscribe-dialog-head">
    <p class="sb-subscribe-eyebrow">Ensaios · Second Brain</p>
    <h2 id="sbSubscribeTitle">Novos ensaios por e-mail.</h2>
    <p>Só quando houver publicação nova.</p>
    <form method="dialog"><button class="sb-subscribe-close" type="submit" aria-label="Fechar">×</button></form>
  </div>''',
'''  <div class="sb-subscribe-dialog-head">
    <h2 id="sbSubscribeTitle">Receba novos ensaios por email.</h2>
    <form method="dialog"><button class="sb-subscribe-close" type="submit" aria-label="Fechar">×</button></form>
  </div>''',
        f'{path.name} title block')
    text = replace_one(text,
        '<p class="sb-subscribe-note"><strong>Importante:</strong> confira também a pasta de <strong>Spam</strong> e confirme o e-mail.</p>',
        '<p class="sb-subscribe-note"><u>Confirme</u> o e-mail recebido. Verifique a <u>caixa de spam</u>. Marque o email como confiável. Você não receberá mensagens de spam.</p>',
        f'{path.name} note')
    path.write_text(text, encoding="utf-8")

# Tiny contract: exact requested hierarchy/copy and actual equal-width box model fix.
for path in [index_path, *essays]:
    text = path.read_text(encoding='utf-8')
    assert text.count('Receba novos ensaios por email.') == 1, path
    assert text.count('<u>Confirme</u> o e-mail recebido.') == 1, path
    assert text.count('<u>caixa de spam</u>') == 1, path
    assert text.count('Você não receberá mensagens de spam.') == 1, path
    assert 'Só quando houver publicação nova.' not in text, path
    assert 'box-sizing:border-box!important;width:100%!important;min-height:44px' in text, path

print(f'public subscribe popup patch PASS; essays={len(essays)}')
