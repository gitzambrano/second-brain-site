#!/usr/bin/env python3
"""Send newly eligible Second Brain essays through Kit API v4.

The current manifest is compared with the previous revision. Re-runs are safe:
each broadcast receives a deterministic description marker and existing Kit
broadcasts are checked before a new one is created.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KIT_API = "https://api.kit.com/v4"
MARKER_PREFIX = "second-brain-newsletter:"


def load_entries(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"invalid newsletter manifest: {path}")
    return [e for e in entries if isinstance(e, dict)]


def entry_key(entry: dict[str, str]) -> str:
    return f"{entry.get('slug', '')}:{entry.get('updated', '')}"


def marker(entry: dict[str, str]) -> str:
    return MARKER_PREFIX + entry_key(entry)


def api_request(api_key: str, method: str, path: str, payload: dict | None = None) -> dict:
    body = None
    headers = {"X-Kit-Api-Key": api_key, "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(KIT_API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kit API {exc.code}: {detail}") from exc


def existing_markers(api_key: str) -> set[str]:
    found: set[str] = set()
    after: str | None = None
    while True:
        suffix = ""
        if after:
            suffix = "?" + urllib.parse.urlencode({"after": after})
        payload = api_request(api_key, "GET", "/broadcasts" + suffix)
        for broadcast in payload.get("broadcasts", []):
            description = str(broadcast.get("description") or "")
            if description.startswith(MARKER_PREFIX):
                found.add(description)
        pagination = payload.get("pagination") or {}
        if not pagination.get("has_next_page"):
            break
        after = pagination.get("end_cursor")
        if not after:
            break
    return found


def broadcast_payload(entry: dict[str, str], base_url: str, template_id: int | None) -> dict:
    url = base_url.rstrip("/") + "/" + str(entry["path"]).lstrip("/")
    title = str(entry["title"]).strip()
    summary = str(entry.get("summary") or "").strip()
    content = (
        f"<p>{html.escape(summary)}</p>"
        f'<p><a href="{html.escape(url, quote=True)}">Ler o essay completo →</a></p>'
    )
    payload: dict = {
        "subject": title,
        "content": content,
        "description": marker(entry),
        "public": False,
        "send_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    if template_id is not None:
        payload["email_template_id"] = template_id
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--previous-manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    current = load_entries(args.manifest)
    previous_keys = {entry_key(e) for e in load_entries(args.previous_manifest)}
    pending = [e for e in current if entry_key(e) not in previous_keys]
    if not pending:
        print("newsletter: no new eligible essays")
        return 0

    base_url = os.environ.get("SITE_BASE_URL", "").strip()
    if not base_url:
        raise SystemExit("SITE_BASE_URL is required")

    if args.dry_run:
        for entry in pending:
            print(f"DRY-RUN {marker(entry)} -> {entry.get('title')}")
        return 0

    api_key = os.environ.get("KIT_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("KIT_API_KEY is required")
    template_raw = os.environ.get("KIT_EMAIL_TEMPLATE_ID", "").strip()
    template_id = int(template_raw) if template_raw else None

    already_sent = existing_markers(api_key)
    for entry in pending:
        identity = marker(entry)
        if identity in already_sent:
            print(f"newsletter: skip existing {identity}")
            continue
        response = api_request(api_key, "POST", "/broadcasts", broadcast_payload(entry, base_url, template_id))
        broadcast = response.get("broadcast") or {}
        print(f"newsletter: created broadcast {broadcast.get('id', '?')} for {entry.get('slug')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, ValueError, RuntimeError) as exc:
        print(f"newsletter: ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
