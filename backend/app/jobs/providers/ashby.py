"""Ashby posting-api JSON (descriptionPlain + workplaceType in the list)."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..http import FetchError, assert_https_allowlist, fetch_json

ID = "ashby"
ALLOWED_HOSTS = {"api.ashbyhq.com"}
TIMEOUT_S = 30.0
RETRIES = 2
_BOARD_RE = re.compile(r"jobs\.ashbyhq\.com/([^/?#]+)", re.IGNORECASE)


def detect(entry: dict[str, Any]) -> str | None:
    try:
        return resolve_api_url(entry)
    except Exception:
        return None


def resolve_api_url(entry: dict[str, Any], *, lean: bool = False) -> str | None:
    if entry.get("api"):
        href = str(entry["api"])
        assert_https_allowlist(href, ALLOWED_HOSTS)
        return href if lean else _with_compensation(href)
    url = str(entry.get("careers_url") or "")
    match = _BOARD_RE.search(url)
    if not match:
        return None
    href = f"https://api.ashbyhq.com/posting-api/job-board/{match.group(1)}"
    return href if lean else _with_compensation(href)


def fetch(entry: dict[str, Any], *, lean: bool = False) -> list[dict[str, Any]]:
    api_url = resolve_api_url(entry, lean=lean)
    if not api_url:
        raise RuntimeError(f"ashby: cannot derive API URL for {entry.get('name')}")
    assert_https_allowlist(api_url, ALLOWED_HOSTS)
    payload = _fetch_with_retry(api_url)
    rows = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []

    company = str(entry.get("name") or "").strip() or "Ashby"
    jobs: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        url = str(row.get("jobUrl") or "").strip()
        if not title or not url:
            continue
        workplace = _workplace(row)
        department = str(row.get("department") or "").strip()
        jobs.append(
            {
                "title": title,
                "url": url,
                "company": company,
                "location": _location(row),
                "description": (
                    "" if lean else str(row.get("descriptionPlain") or "").strip()
                ),
                "posted_at": row.get("publishedAt"),
                "tags": [department] if department else [],
                "workplace": workplace,
            }
        )
    return jobs


def _fetch_with_retry(url: str) -> Any:
    last_error: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            return fetch_json(url, ALLOWED_HOSTS, timeout_s=TIMEOUT_S)
        except FetchError as exc:
            last_error = exc
            message = str(exc).lower()
            retryable = (
                exc.status in (429, 502, 503)
                or "timeout" in message
                or "http 429" in message
                or "http 503" in message
            )
            if not retryable or attempt == RETRIES:
                raise
            time.sleep(1.0 * (attempt + 1))
    raise last_error or FetchError("ashby: fetch failed")


def _with_compensation(url: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("includeCompensation", "true")
    return urlunparse(parsed._replace(query=urlencode(query)))


def _workplace(row: dict[str, Any]) -> str | None:
    wt = str(row.get("workplaceType") or "").strip().lower()
    if wt == "remote":
        return "remote"
    if wt == "hybrid":
        return "hybrid"
    if wt == "onsite":
        return "onsite"
    if row.get("isRemote") is True:
        return "remote"
    return None


def _location(row: dict[str, Any]) -> str:
    parts: list[str] = []
    primary = str(row.get("location") or "").strip()
    if primary:
        parts.append(primary)
    for extra in row.get("secondaryLocations") or []:
        if not isinstance(extra, dict):
            continue
        loc = str(extra.get("location") or "").strip()
        if loc:
            parts.append(loc)
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        key = part.lower()
        if key not in seen:
            seen.add(key)
            unique.append(part)
    return " · ".join(unique)
