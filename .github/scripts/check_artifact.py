#!/usr/bin/env python3
"""
Portaria do repositório público, antes do deploy.

Este repositório é uma projeção: o conteúdo chega pronto do engine, que já roda
`check_site_privacy.py` na origem. Mesmo assim, o que é publicado na internet
não deveria confiar cegamente no que recebeu — um push manual, um merge errado
ou um engine numa versão antiga chegam aqui do mesmo jeito que uma publicação
legítima, e antes disto o workflow apenas empacotava e mandava para o ar.

A checagem é auto-suficiente de propósito: só a biblioteca padrão, só os
arquivos deste repositório. Ela **não** clona o repo privado e **não** recebe
credencial nenhuma — se precisasse do corpus para decidir, deixaria de ser uma
portaria e viraria mais uma cópia do vazamento.

O que reprova o deploy:

0. arquivo fora da allowlist de caminhos do artefato;
1. página de essay sem autorização no `site-manifest.json`;
2. essay autorizado sem página;
3. corpo de texto no `search-index.json` (o índice é catálogo, não corpus);
4. caminho para dentro do repositório privado (`data/` inteiro — `wiki/`, `plan/`,
   `raw/`, `output/`, `.obsidian/` e o que mais vier) vazando em qualquer arquivo;
5. caminho absoluto de máquina vazando em qualquer arquivo;
6. artefato acima do orçamento de tamanho.

A regra 0 é a que muda o caráter da portaria. As regras 3 a 5 leem conteúdo, e
só de alguns tipos de texto: um `.zip`, um `.pdf`, um binário qualquer ou um
arquivo esquecido na raiz atravessavam a checagem inteira sem ninguém olhar,
porque nenhuma regra perguntava se aquele arquivo tinha o direito de existir.
A allowlist inverte o ônus: o build gera um conjunto conhecido de caminhos, e
o que não corresponde a nenhum deles reprova por padrão.

Uso:
    python .github/scripts/check_artifact.py            # audita o checkout
    python .github/scripts/check_artifact.py _site      # audita a pasta a publicar
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# `data/` é a raiz do repositório privado INTEIRA, não só `data/wiki/`: o corpus
# convive ali com `data/plan/`, `data/raw/`, `data/output/` e `data/.obsidian/`,
# e um caminho para qualquer um deles denuncia estrutura privada do mesmo jeito.
# Ancorar em `wiki/` deixava os outros quatro passarem — e, pior, deixaria passar
# qualquer subpasta nova que o repo privado ganhasse depois. Por isso a barreira
# é o separador logo após `data`, não o nome da subpasta.
#
# O lookbehind `(?<!\w)` é o que separa caminho de coincidência: `data` só conta
# quando não é sufixo de outra palavra (`metadata/`, `userdata/`), e exigir `/`
# ou `\` logo em seguida descarta os usos legítimos e frequentes no HTML gerado
# — `data-status="..."`, `data-tags=`, `data:image/svg+xml`, `.data` em JS. O
# `.` fica FORA do lookbehind de propósito: `./data/wiki/x.md` e `../data/raw/`
# são justamente as formas relativas que um vazamento assumiria.
PRIVATE_PATH_RE = re.compile(r"(?<!\w)data[/\\]")

# Caminho absoluto de máquina: `C:\Users\...`, `/home/...`, `/Users/...`.
LOCAL_PATH_RE = re.compile(r"[A-Za-z]:\\Users\\|/home/[a-z]|/Users/[A-Za-z]")

BUDGETS_KB = {
    "index.html": 400,
    "404.html": 32,
    "graph.html": 1200,
    "sphere.html": 900,
    "graph.json": 1600,
    "search-index.json": 400,
    "site-manifest.json": 64,
}

TEXT_SUFFIXES = {".html", ".json", ".js", ".css", ".txt", ".md", ".xml", ".svg"}

# ---------------------------------------------------------------------------
# Allowlist de caminhos
# ---------------------------------------------------------------------------
# Espelha, em padrões, o que `scripts/build_site.py` produz no engine:
# `GENERATED_ROOT_FILES`, `GENERATED_DIRS`, `FRONTEND_ASSETS` e `BRAND_ASSETS`,
# mais o que os passos auxiliares deixam em `assets/` (fontes auto-hospedadas,
# bundle local do MathJax, imagens dos essays, capas do cartão social).
#
# São padrões e não a lista literal de arquivos por um motivo prático: a lista
# literal teria duzentas linhas e ficaria desatualizada no primeiro essay novo,
# e uma portaria que reprova o build legítimo é desligada na semana seguinte. O
# padrão é apertado onde importa — extensão e diretório — e frouxo só no nome.
#
# Sintaxe: `fnmatch` por segmento, `*` não atravessa `/`; `**` no fim libera a
# subárvore inteira.
ARTIFACT_ALLOWLIST = (
    # Marcador que impede o Jekyll do Pages de comer diretórios com underscore
    # e de reprocessar o HTML já pronto. Vai ao ar; sem ele o site quebra.
    ".nojekyll",
    # GENERATED_ROOT_FILES
    "index.html",
    "404.html",
    "graph.html",
    "sphere.html",
    "graph.json",
    "search-index.json",
    "site-manifest.json",
    # GENERATED_DIRS: uma página por essay autorizado. As regras 1 e 2 conferem
    # nome por nome contra o manifesto; aqui só se garante que nada além de
    # `.html` mora nessa pasta.
    "essays/*.html",
    # FRONTEND_ASSETS
    "assets/site.css",
    "assets/site.js",
    "assets/theme.js",
    "assets/essay.js",
    # BRAND_ASSETS, assados por `build_favicons.py` e copiados como estão.
    "assets/favicon.ico",
    "assets/icon-16.png",
    "assets/icon-32.png",
    "assets/icon-32-dark.png",
    "assets/icon-light-192.png",
    "assets/icon-dark-192.png",
    "assets/icon-light-512.png",
    "assets/icon-dark-512.png",
    "assets/apple-touch-icon.png",
    # Capas do cartão social (Open Graph), uma por tema.
    "assets/cover-light.png",
    "assets/cover-dark.png",
    # Fonte auto-hospedada: a folha e os arquivos binários que ela referencia.
    # O nome do `.woff2` vem do Google Fonts e muda a cada revisão da fonte, por
    # isso o padrão é por extensão e não por nome.
    "assets/fonts/fonts.css",
    "assets/fonts/*.woff2",
    # MathJax local: o build baixa um único bundle para o leitor não depender de
    # CDN de terceiro.
    "assets/mathjax/tex-svg.js",
    # Imagens dos essays. Fechado por extensão de propósito: é a pasta em que um
    # `.pdf` ou um `.zip` esquecido teria a chance mais plausível de entrar de
    # carona junto com as figuras.
    "assets/media/*.png",
    "assets/media/*.webp",
    "assets/media/*.jpg",
    "assets/media/*.jpeg",
    "assets/media/*.gif",
    "assets/media/*.svg",
)

# Administrativo: existe no repositório, nunca no artefato publicado.
#
# A linha divisória entre "legítimo no repo" e "legítimo no ar" é justamente
# esta lista. O workflow monta `_site/` sem nenhum destes caminhos, e então a
# portaria roda em modo `artifact`, onde a presença de qualquer um reprova.
# (`.git/` não aparece aqui: tem tratamento próprio na varredura, para não
# despejar o histórico inteiro na saída quando estiver no lugar errado.)
REPO_ONLY_ALLOWLIST = (
    ".github/**",
    ".gitignore",
    ".second-brain-site",
    "README.md",
)


def path_matches(relative: str, pattern: str) -> bool:
    """Casa `relative` (POSIX) contra um padrão segmento a segmento.

    O `fnmatch` cru não serve: nele `*` atravessa `/`, de modo que `assets/*.js`
    aceitaria `assets/qualquer/coisa.js` e a allowlist perderia a precisão que é
    a razão de existir. Aqui cada segmento é comparado isoladamente e o número
    de segmentos tem de bater, salvo quando o padrão termina em `**`.
    """
    parts = relative.split("/")
    pattern_parts = pattern.split("/")
    if pattern_parts[-1] == "**":
        prefix = pattern_parts[:-1]
        if len(parts) <= len(prefix):
            return False
        return all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, prefix))
    if len(parts) != len(pattern_parts):
        return False
    return all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, pattern_parts))


def allowed(relative: str, patterns: tuple[str, ...]) -> bool:
    return any(path_matches(relative, pattern) for pattern in patterns)


def detect_mode(root: Path) -> str:
    """Decide se `root` é o checkout do repositório ou a pasta a publicar.

    O marcador é `.github/`: ele só existe no repositório e o passo de montagem
    do workflow nunca o copia. Assim o comando sem argumento continua auditando
    o checkout — que legitimamente tem `README.md` e `.gitignore` — enquanto o
    mesmo script, apontado para `_site/`, exige a árvore limpa.
    """
    return "repo" if (root / ".github").is_dir() else "artifact"


def fail(problems: list[str], message: str) -> None:
    problems.append(message)


def check(root: Path, mode: str) -> list[str]:
    problems: list[str] = []

    patterns = ARTIFACT_ALLOWLIST
    if mode == "repo":
        patterns = patterns + REPO_ONLY_ALLOWLIST

    manifest_path = root / "site-manifest.json"
    if not manifest_path.is_file():
        return ["site-manifest.json ausente; nada a validar contra"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    published = set(manifest.get("published", []))
    if not published:
        fail(problems, "site-manifest.json não lista nenhum essay autorizado")

    # 0: allowlist. Percorre a árvore inteira, inclusive binários, e reprova o
    # que não corresponde a nenhum padrão conhecido do build.
    #
    # `.git/` é tratado à parte para não despejar milhares de objetos soltos na
    # saída: no repositório ele é esperado e se cala; num `_site/` ele é um
    # achado grave — o histórico inteiro iria ao ar — e vira uma linha só.
    if (root / ".git").exists() and mode == "artifact":
        fail(problems, "diretório .git dentro do artefato: o histórico do repositório iria ao ar")
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
        # Um symlink escapa da allowlist por definição: o caminho está na lista,
        # o conteúdo servido está em outro lugar. O build nunca cria nenhum.
        if path.is_symlink():
            fail(problems, f"symlink no artefato: {relative}")
            continue
        if not path.is_file():
            continue
        if not allowed(relative, patterns):
            fail(problems, f"arquivo fora da allowlist do artefato: {relative}")

    # 1 e 2: a allowlist e as páginas têm de coincidir exatamente.
    pages = {p.stem for p in (root / "essays").glob("*.html")}
    for slug in sorted(pages - published):
        fail(problems, f"página publicada sem autorização no manifesto: essays/{slug}.html")
    for slug in sorted(published - pages):
        fail(problems, f"essay autorizado sem página renderizada: {slug}")

    # 3: o índice de busca é catálogo, não corpus.
    search_path = root / "search-index.json"
    if search_path.is_file():
        for entry in json.loads(search_path.read_text(encoding="utf-8")):
            slug = entry.get("slug")
            if entry.get("text"):
                fail(problems, f"search-index.json carrega corpo de texto: {slug}")
            if not entry.get("published") and entry.get("url"):
                fail(problems, f"essay não autorizado com link: {slug}")
            if entry.get("published") and slug not in published:
                fail(problems, f"entrada marcada como publicada fora da allowlist: {slug}")

    # 4 e 5: nenhum caminho interno vaza. `.github/` fica de fora porque a
    # própria portaria cita `data/` na regex e reprovaria a si mesma.
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts or ".github" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(root).as_posix()
        if PRIVATE_PATH_RE.search(text):
            fail(problems, f"caminho do repositório privado em {relative}")
        if LOCAL_PATH_RE.search(text):
            fail(problems, f"caminho absoluto de máquina em {relative}")

    # 6: orçamento de tamanho.
    for name, limit in BUDGETS_KB.items():
        target = root / name
        if not target.is_file():
            continue
        kb = target.stat().st_size / 1024
        if kb > limit:
            fail(problems, f"{name}: {kb:.0f} KB excede o teto de {limit} KB")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Portaria do artefato público antes do deploy.")
    parser.add_argument(
        "target",
        nargs="?",
        default=str(ROOT),
        help="diretório a auditar (padrão: a raiz deste repositório)",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "repo", "artifact"),
        default="auto",
        help="'repo' tolera README/.gitignore/.github; 'artifact' exige a árvore limpa (padrão: auto)",
    )
    args = parser.parse_args(argv)

    root = Path(args.target).resolve()
    if not root.is_dir():
        print(f"FAIL: alvo inexistente: {root}")
        return 1
    mode = detect_mode(root) if args.mode == "auto" else args.mode

    problems = check(root, mode)
    if problems:
        print(f"FAIL: {len(problems)} problema(s) antes do deploy [{root.name}, modo {mode}]")
        for item in problems:
            print(f"  - {item}")
        return 1

    pages = len(list((root / "essays").glob("*.html")))
    print(
        f"PASS: {pages} página(s) autorizada(s), allowlist limpa, nenhum vazamento, "
        f"tamanho dentro do teto [{root.name}, modo {mode}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
