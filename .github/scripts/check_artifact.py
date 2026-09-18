#!/usr/bin/env python3
"""Minimal publication gate: require a valid privacy seal for these exact bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "site-manifest.json"
TEXT_SUFFIXES = {".html", ".json", ".js", ".css", ".txt", ".md", ".xml", ".svg"}
SKIP_PARTS = {".git", ".github"}
SKIP_ROOT = {"README.md", ".gitignore", ".second-brain-site", "site-manifest.json"}


def digest() -> str:
    h = hashlib.sha256()
    files = sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and not (SKIP_PARTS & set(path.relative_to(ROOT).parts))
            and not (path.parent == ROOT and path.name in SKIP_ROOT)
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    for path in files:
        data = path.read_bytes()
        if path.suffix.lower() in TEXT_SUFFIXES:
            data = data.replace(b"\r\n", b"\n")
        h.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def main() -> int:
    try:
        seal = json.loads(MANIFEST.read_text(encoding="utf-8"))["seal"]
        expected = seal["artifact_digest"]
        gates = seal["gates"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"privacy gate: invalid or missing seal: {exc}") from exc

    if "privacy" not in gates:
        raise SystemExit("privacy gate: seal does not contain privacy")

    actual = digest()
    if actual != expected:
        raise SystemExit(f"privacy gate: artifact changed after it was sealed (actual={actual})")

    print(f"privacy gate: OK ({actual[:16]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
