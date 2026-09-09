// Controle de tema compartilhado. O valor inicial é aplicado por um trecho
// inline no <head> de cada página, para a primeira pintura já sair na paleta
// certa; este arquivo só liga o botão e guarda a escolha. A preferência do
// sistema não é consultada: sem escolha guardada, o site abre no claro.
(function () {
  var root = document.documentElement;

  function apply(theme, persist) {
    root.dataset.theme = theme;
    var button = document.getElementById('themeToggle');
    if (button) {
      button.setAttribute('aria-pressed', String(theme === 'light'));
      button.setAttribute(
        'aria-label', theme === 'light' ? 'Mudar para tema escuro' : 'Mudar para tema claro'
      );
    }
    if (persist) {
      try { localStorage.setItem('sb-theme', theme); } catch (e) { /* private mode */ }
    }
  }

  apply(root.dataset.theme || 'light', false);

  document.getElementById('themeToggle')?.addEventListener('click', function () {
    apply(root.dataset.theme === 'dark' ? 'light' : 'dark', true);
  });

})();

/* Newsletter signup. The canonical generator now renders this directly in the
   landing page. This runtime injection keeps the currently sealed projection
   intact while publishing the same surface without rebuilding private data. */
(function () {
  if (!document.body || !document.body.classList.contains('landing')) return;
  if (document.getElementById('subscribeOpen')) return;

  var nav = document.querySelector('.topnav');
  var themeToggle = document.getElementById('themeToggle');
  if (!nav || !themeToggle) return;

  var brand = document.querySelector('.brand');
  if (brand && !brand.hasAttribute('aria-label')) brand.setAttribute('aria-label', 'Second Brain');

  var style = document.createElement('style');
  style.id = 'subscribeRuntimeStyles';
  style.textContent = [
    '.subscribe-cta{display:inline-flex;align-items:center;justify-content:center;min-height:34px;padding:0 12px;border:1px solid color-mix(in srgb,var(--accent) 42%,var(--line));border-radius:999px;background:var(--accent-soft);color:var(--accent);font:650 12.5px var(--sans);cursor:pointer;transition:border-color .16s var(--ease),background .16s var(--ease),color .16s var(--ease)}',
    '.subscribe-cta:hover{border-color:color-mix(in srgb,var(--accent) 72%,var(--line));background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--text-strong)}',
    '.subscribe-dialog{width:min(430px,calc(100% - 28px));max-height:min(640px,calc(100dvh - 32px));margin:auto;padding:0;border:1px solid var(--line-strong);border-radius:18px;background:var(--panel);color:var(--text);box-shadow:var(--shadow);overflow:auto}',
    '.subscribe-dialog::backdrop{background:rgba(0,0,0,.54);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)}',
    '.subscribe-dialog-head{position:relative;padding:24px 52px 0 24px}',
    '.subscribe-dialog-eyebrow{margin:0 0 5px;color:var(--accent);font:700 9.5px var(--mono);letter-spacing:.17em;text-transform:uppercase}',
    '.subscribe-dialog h2{margin:0 0 7px;color:var(--text-strong);font:600 1.55rem/1.22 var(--serif);letter-spacing:-.025em}',
    '.subscribe-dialog-lede{margin:0;color:var(--muted);font-size:13.5px;line-height:1.5}',
    '.subscribe-close{position:absolute;top:16px;right:16px;width:34px;height:34px;display:grid;place-items:center;padding:0;border:1px solid var(--line);border-radius:9px;background:transparent;color:var(--muted);font-size:19px;line-height:1;cursor:pointer}',
    '.subscribe-close:hover{color:var(--text-strong);border-color:var(--line-strong)}',
    '.subscribe-embed{min-width:0;padding:18px 24px 24px}',
    '.subscribe-embed .formkit-form{max-width:none!important;margin:0!important;padding:0!important;border:0!important;background:transparent!important;box-shadow:none!important}',
    '.subscribe-embed .formkit-header,.subscribe-embed .formkit-subheader,.subscribe-embed [data-element="header"],.subscribe-embed [data-element="subheader"]{display:none!important}',
    '.subscribe-embed .formkit-fields{display:flex!important;flex-direction:column!important;gap:8px!important;margin:0!important}',
    '.subscribe-embed .formkit-field{margin:0!important}',
    '.subscribe-embed .formkit-input{width:100%!important;min-height:44px!important;margin:0!important;padding:0 13px!important;border:1px solid var(--line-strong)!important;border-radius:10px!important;outline:0!important;background:var(--panel-2)!important;color:var(--text)!important;box-shadow:none!important;font-family:var(--sans)!important;font-size:13.5px!important}',
    '.subscribe-embed .formkit-input:focus{border-color:color-mix(in srgb,var(--accent) 62%,var(--line))!important}',
    '.subscribe-embed .formkit-submit{width:100%!important;min-height:44px!important;margin:0!important;padding:0 16px!important;border:1px solid transparent!important;border-radius:10px!important;background:var(--accent)!important;color:var(--bg)!important;box-shadow:none!important;font-family:var(--sans)!important;font-size:13px!important;font-weight:700!important;cursor:pointer!important}',
    '.subscribe-embed .formkit-submit:hover{background:var(--accent-dim)!important}',
    '.subscribe-embed .formkit-guarantee{margin:8px 0 0!important;color:var(--faint)!important;font-family:var(--sans)!important;font-size:10.5px!important;line-height:1.4!important}',
    '.subscribe-embed .formkit-powered-by-convertkit-container{margin-top:6px!important;opacity:.62}',
    '@media(max-width:760px){.topnav .nav-link.active{display:none}.subscribe-cta{min-height:32px;padding-inline:10px;font-size:12px}.subscribe-dialog-head{padding:22px 48px 0 20px}.subscribe-embed{padding:16px 20px 20px}.subscribe-dialog h2{font-size:1.4rem}}',
    '@media(max-width:360px){.brand{gap:0}.brand>span:last-child{display:none}.topnav{gap:8px}.subscribe-cta{padding-inline:9px}}'
  ].join('\n');
  document.head.appendChild(style);

  var open = document.createElement('button');
  open.className = 'subscribe-cta';
  open.type = 'button';
  open.id = 'subscribeOpen';
  open.setAttribute('aria-haspopup', 'dialog');
  open.setAttribute('aria-controls', 'subscribeDialog');
  open.textContent = 'Assinar';
  nav.insertBefore(open, themeToggle);

  var dialog = document.createElement('dialog');
  dialog.className = 'subscribe-dialog';
  dialog.id = 'subscribeDialog';
  dialog.setAttribute('aria-labelledby', 'subscribeTitle');
  dialog.innerHTML = '<div class="subscribe-dialog-head">' +
    '<p class="subscribe-dialog-eyebrow">Second Brain</p>' +
    '<h2 id="subscribeTitle">Receba novos essays</h2>' +
    '<p class="subscribe-dialog-lede">Um e-mail quando eu publicar algo novo.</p>' +
    '<form method="dialog"><button class="subscribe-close" type="submit" aria-label="Fechar">×</button></form>' +
    '</div><div class="subscribe-embed" aria-label="Assinar a newsletter do Second Brain"></div>';
  document.body.appendChild(dialog);

  var kit = document.createElement('script');
  kit.async = true;
  kit.dataset.uid = '4fd36350af';
  kit.src = 'https://gustavo-jose-zambrano.kit.com/4fd36350af/index.js';
  dialog.querySelector('.subscribe-embed').appendChild(kit);

  if (typeof dialog.showModal === 'function') {
    open.addEventListener('click', function () { dialog.showModal(); });
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) dialog.close();
    });
  }
})();
