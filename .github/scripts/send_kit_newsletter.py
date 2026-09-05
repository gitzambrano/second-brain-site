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
from typing import Any

KIT_API = "https://api.kit.com/v4"
DEFAULT_SITE_BASE_URL = "https://gitzambrano.github.io/second-brain-site"
MARKER_PREFIX = "second-brain-newsletter:"


def load_entries(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"invalid newsletter manifest: {path}")
    return [entry for entry in entries if isinstance(entry, dict)]


def entry_key(entry: dict[str, Any]) -> str:
    identity = str(entry.get("id") or "").strip()
    if identity:
        return identity
    slug = str(entry.get("slug") or "").strip()
    if not slug:
        raise ValueError("newsletter entry without id or slug")
    return slug


def marker(entry: dict[str, Any]) -> str:
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


def email_content(entry: dict[str, Any], url: str) -> str:
    title = html.escape(str(entry.get("title") or "").strip())
    summary = html.escape(str(entry.get("summary") or "").strip())
    minutes = int(entry.get("minutes") or 0)
    escaped_url = html.escape(url, quote=True)
    reading = f"{minutes} min de leitura" if minutes > 0 else ""

    parts = [
        '<p style="margin:0 0 10px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;">Second Brain</p>',
        f'<h1 style="margin:0 0 18px;font-size:28px;line-height:1.18;">{title}</h1>',
    ]
    if summary:
        parts.append(f'<p style="margin:0 0 16px;font-size:17px;line-height:1.6;">{summary}</p>')
    if reading:
        parts.append(f'<p style="margin:0 0 22px;font-size:14px;opacity:.72;">{reading}</p>')
    parts.extend(
        [
            f'<p style="margin:0 0 26px;"><a href="{escaped_url}" style="font-weight:600;">Ler o essay completo →</a></p>',
            '<p style="margin:26px 0 0;font-size:13px;opacity:.7;">Gustavo Zambrano · Second Brain</p>',
        ]
    )
    return "".join(parts)


def broadcast_payload(
    entry: dict[str, Any],
    base_url: str,
    template_id: int | None,
    now: dt.datetime | None = None,
) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    now = now.replace(microsecond=0)
    send_at = now + dt.timedelta(minutes=1)
    url = base_url.rstrip("/") + "/" + str(entry["path"]).lstrip("/")

    payload: dict[str, Any] = {
        "subject": str(entry.get("subject") or entry.get("title") or "Novo essay").strip(),
        "preview_text": str(entry.get("preview_text") or entry.get("summary") or "").strip(),
        "content": email_content(entry, url),
        "description": marker(entry),
        "public": False,
        "published_at": now.isoformat(),
        "send_at": send_at.isoformat(),
    }
    if template_id is not None:
        payload["email_template_id"] = template_id
    return payload


def pending_entries(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_keys = {entry_key(entry) for entry in previous}
    return [entry for entry in current if entry_key(entry) not in previous_keys]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--previous-manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    current = load_entries(args.manifest)
    previous = load_entries(args.previous_manifest)
    pending = pending_entries(current, previous)
    if not pending:
        print("newsletter: no new eligible essays")
        return 0

    base_url = os.environ.get("SITE_BASE_URL", DEFAULT_SITE_BASE_URL).strip() or DEFAULT_SITE_BASE_URL

    if args.dry_run:
        for entry in pending:
            payload = broadcast_payload(entry, base_url, None)
            print(f"DRY-RUN {marker(entry)}")
            print(f"  subject: {payload['subject']}")
            print(f"  preview: {payload['preview_text']}")
            print(f"  url: {base_url.rstrip('/')}/{str(entry['path']).lstrip('/')}")
        return 0

    api_key = os.environ.get("KIT_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("KIT_API_KEY is required when newsletter sending is enabled")
    template_raw = os.environ.get("KIT_EMAIL_TEMPLATE_ID", "").strip()
    template_id = int(template_raw) if template_raw else None

    already_sent = existing_markers(api_key)
    for entry in pending:
        identity = marker(entry)
        if identity in already_sent:
            print(f"newsletter: skip existing {identity}")
            continue
        payload = broadcast_payload(entry, base_url, template_id)
        response = api_request(api_key, "POST", "/broadcasts", payload)
        broadcast = response.get("broadcast") or {}
        print(f"newsletter: scheduled broadcast {broadcast.get('id', '?')} for {entry.get('slug')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"newsletter: ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
