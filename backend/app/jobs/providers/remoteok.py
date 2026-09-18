"""Board-wide RemoteOK JSON feed. Index 0 is metadata and is skipped."""

from __future__ import annotations

from typing import Any

from ..http import fetch_json
from ..text import html_to_text

ID = "remoteok"
FEED_URL = "https://remoteok.com/api"
ALLOWED_HOSTS = {"remoteok.com", "www.remoteok.com"}


def detect(entry: dict[str, Any]) -> str | None:
    if (entry.get("provider") or "") == ID:
        return FEED_URL
    return None


def fetch(entry: dict[str, Any]) -> list[dict[str, Any]]:
    payload = fetch_json(FEED_URL, ALLOWED_HOSTS)
    if not isinstance(payload, list):
        raise RuntimeError("remoteok: expected a JSON array")

    company_fallback = (entry.get("name") or "RemoteOK").strip()
    jobs: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        title = str(row.get("position") or row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        if not title or not url:
            continue
        tags = [
            str(tag).strip()
            for tag in (row.get("tags") or [])
            if str(tag).strip()
        ]
        epoch = row.get("epoch") or row.get("date")
        posted_at = epoch
        if isinstance(epoch, str) and epoch.isdigit():
            posted_at = int(epoch)
        elif isinstance(epoch, (int, float)):
            posted_at = float(epoch)
        jobs.append(
            {
                "title": title,
                "url": url,
                "company": str(row.get("company") or "").strip() or company_fallback,
                "location": str(row.get("location") or "").strip() or "Remote",
                "description": html_to_text(row.get("description") or ""),
                "posted_at": posted_at,
                "tags": tags,
                "workplace": "remote",
            }
        )
    return jobs
