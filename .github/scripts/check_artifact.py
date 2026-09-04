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

1. página de essay sem autorização no `site-manifest.json`;
2. essay autorizado sem página;
3. corpo de texto no `search-index.json` (o índice é catálogo, não corpus);
4. caminho para dentro do repositório privado (`data/` inteiro — `wiki/`, `plan/`,
   `raw/`, `output/`, `.obsidian/` e o que mais vier) vazando em qualquer arquivo;
5. caminho absoluto de máquina vazando em qualquer arquivo;
6. artefato acima do orçamento de tamanho.

Uso:
    python .github/scripts/check_artifact.py
"""
from __future__ import annotations

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


def fail(problems: list[str], message: str) -> None:
    problems.append(message)


def main() -> int:
    problems: list[str] = []

    manifest_path = ROOT / "site-manifest.json"
    if not manifest_path.is_file():
        print("FAIL: site-manifest.json ausente; nada a validar contra")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    published = set(manifest.get("published", []))
    if not published:
        fail(problems, "site-manifest.json não lista nenhum essay autorizado")

    # 1 e 2: a allowlist e as páginas têm de coincidir exatamente.
    pages = {p.stem for p in (ROOT / "essays").glob("*.html")}
    for slug in sorted(pages - published):
        fail(problems, f"página publicada sem autorização no manifesto: essays/{slug}.html")
    for slug in sorted(published - pages):
        fail(problems, f"essay autorizado sem página renderizada: {slug}")

    # 3: o índice de busca é catálogo, não corpus.
    search_path = ROOT / "search-index.json"
    if search_path.is_file():
        for entry in json.loads(search_path.read_text(encoding="utf-8")):
            slug = entry.get("slug")
            if entry.get("text"):
                fail(problems, f"search-index.json carrega corpo de texto: {slug}")
            if not entry.get("published") and entry.get("url"):
                fail(problems, f"essay não autorizado com link: {slug}")
            if entry.get("published") and slug not in published:
                fail(problems, f"entrada marcada como publicada fora da allowlist: {slug}")

    # 4 e 5: nenhum caminho interno vaza.
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or ".github" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(ROOT).as_posix()
        if PRIVATE_PATH_RE.search(text):
            fail(problems, f"caminho do repositório privado em {relative}")
        if LOCAL_PATH_RE.search(text):
            fail(problems, f"caminho absoluto de máquina em {relative}")

    # 6: orçamento de tamanho.
    for name, limit in BUDGETS_KB.items():
        target = ROOT / name
        if not target.is_file():
            continue
        kb = target.stat().st_size / 1024
        if kb > limit:
            fail(problems, f"{name}: {kb:.0f} KB excede o teto de {limit} KB")

    if problems:
        print(f"FAIL: {len(problems)} problema(s) antes do deploy")
        for item in problems:
            print(f"  - {item}")
        return 1

    print(f"PASS: {len(pages)} página(s) autorizada(s), nenhum vazamento, tamanho dentro do teto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
