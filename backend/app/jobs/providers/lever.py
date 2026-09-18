"""Lever public postings JSON (descriptionPlain is in the list payload)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from ..http import assert_https_allowlist, fetch_json

ID = "lever"
ALLOWED_HOSTS = {"api.lever.co", "api.eu.lever.co"}
_JOBS_HOST_RE = re.compile(r"^jobs\.((?:eu\.)?lever\.co)$", re.IGNORECASE)


def detect(entry: dict[str, Any]) -> str | None:
    try:
        return resolve_api_url(entry)
    except Exception:
        return None


def resolve_api_url(entry: dict[str, Any]) -> str | None:
    if entry.get("api"):
        href = str(entry["api"])
        assert_https_allowlist(href, ALLOWED_HOSTS)
        return href
    try:
        parsed = urlparse(str(entry.get("careers_url") or ""))
    except ValueError:
        return None
    host_match = _JOBS_HOST_RE.match(parsed.hostname or "")
    if not host_match:
        return None
    slug = next((part for part in parsed.path.split("/") if part), "")
    if not slug:
        return None
    return f"https://api.{host_match.group(1).lower()}/v0/postings/{slug}"


def fetch(entry: dict[str, Any], *, lean: bool = False) -> list[dict[str, Any]]:
    api_url = resolve_api_url(entry)
    if not api_url:
        raise RuntimeError(f"lever: cannot derive API URL for {entry.get('name')}")
    assert_https_allowlist(api_url, ALLOWED_HOSTS)
    payload = fetch_json(api_url, ALLOWED_HOSTS)
    if not isinstance(payload, list):
        return []

    company = str(entry.get("name") or "").strip() or "Lever"
    jobs: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        title = str(row.get("text") or "").strip()
        url = str(row.get("hostedUrl") or "").strip()
        if not title or not url:
            continue
        categories = row.get("categories") if isinstance(row.get("categories"), dict) else {}
        location = _location(categories)
        commitment = str(categories.get("commitment") or "").strip()
        team = str(categories.get("team") or "").strip()
        tags = [item for item in (team, commitment) if item]
        description = (
            "" if lean else str(row.get("descriptionPlain") or "").strip()
        )
        jobs.append(
            {
                "title": title,
                "url": url,
                "company": company,
                "location": location,
                "description": description,
                "posted_at": row.get("createdAt"),
                "tags": tags,
                "raw_type": commitment,
            }
        )
    return jobs


def _location(categories: dict[str, Any]) -> str:
    parts: list[str] = []
    primary = str(categories.get("location") or "").strip()
    extra = categories.get("allLocations")
    candidates = [primary]
    if isinstance(extra, list):
        candidates.extend(str(item).strip() for item in extra)
    seen: set[str] = set()
    for item in candidates:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            parts.append(item)
    return "; ".join(parts)
