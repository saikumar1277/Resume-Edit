"""Board-wide Remotive JSON feed — no company slug required."""

from __future__ import annotations

from typing import Any

from ..http import fetch_json
from ..text import html_to_text

ID = "remotive"
FEED_URL = "https://remotive.com/api/remote-jobs"
ALLOWED_HOSTS = {"remotive.com", "www.remotive.com"}

_TYPE_MAP = {
    "full_time": "full-time",
    "part_time": "part-time",
    "contract": "contract",
    "freelance": "contract",
    "internship": "internship",
}


def detect(entry: dict[str, Any]) -> str | None:
    if (entry.get("provider") or "") == ID:
        return FEED_URL
    return None


def fetch(entry: dict[str, Any]) -> list[dict[str, Any]]:
    payload = fetch_json(FEED_URL, ALLOWED_HOSTS)
    rows = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("remotive: expected { jobs: [...] }")

    company_fallback = (entry.get("name") or "Remotive").strip()
    jobs: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        if not title or not url:
            continue
        raw_type = str(row.get("job_type") or "").strip().lower()
        tags = [
            str(tag).strip()
            for tag in (row.get("tags") or [])
            if str(tag).strip()
        ]
        category = str(row.get("category") or "").strip()
        if category and category not in tags:
            tags.insert(0, category)
        jobs.append(
            {
                "title": title,
                "url": url,
                "company": str(row.get("company_name") or "").strip()
                or company_fallback,
                "location": str(row.get("candidate_required_location") or "").strip(),
                "description": html_to_text(row.get("description") or ""),
                "posted_at": row.get("publication_date"),
                "tags": tags,
                "workplace": "remote",
                "type": _TYPE_MAP.get(raw_type),
                "raw_type": raw_type,
            }
        )
    return jobs
