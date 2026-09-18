"""Greenhouse boards-api JSON. Lean list omits content=true (no JD)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from ..http import assert_https_allowlist, fetch_json
from ..text import html_to_text

ID = "greenhouse"
ALLOWED_HOSTS = {
    "boards-api.greenhouse.io",
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "job-boards.eu.greenhouse.io",
}
_BOARD_RE = re.compile(
    r"(?:job-boards(?:\.eu)?|boards)\.greenhouse\.io/([^/?#]+)",
    re.IGNORECASE,
)
_API_RE = re.compile(
    r"boards-api\.greenhouse\.io/v1/boards/([^/?#]+)",
    re.IGNORECASE,
)


def detect(entry: dict[str, Any]) -> str | None:
    try:
        return resolve_api_url(entry)
    except Exception:
        return None


def resolve_api_url(entry: dict[str, Any]) -> str | None:
    if entry.get("api"):
        return _jobs_api_url(str(entry["api"]))
    url = str(entry.get("careers_url") or "")
    match = _API_RE.search(url) or _BOARD_RE.search(url)
    if not match:
        return None
    return f"https://boards-api.greenhouse.io/v1/boards/{match.group(1)}/jobs"


def fetch(entry: dict[str, Any], *, lean: bool = False) -> list[dict[str, Any]]:
    api_url = resolve_api_url(entry)
    if not api_url:
        raise RuntimeError(f"greenhouse: cannot derive API URL for {entry.get('name')}")
    list_url = api_url if lean else _with_content(api_url)
    assert_https_allowlist(list_url, ALLOWED_HOSTS)
    payload = fetch_json(list_url, ALLOWED_HOSTS)
    rows = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []

    company = str(entry.get("name") or "").strip() or "Greenhouse"
    jobs: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = str(row.get("absolute_url") or "").strip()
        title = str(row.get("title") or "").strip()
        if not url or not title:
            continue
        location = ""
        loc = row.get("location")
        if isinstance(loc, dict):
            location = str(loc.get("name") or "").strip()
        elif isinstance(loc, str):
            location = loc.strip()
        departments = []
        for dept in row.get("departments") or []:
            if isinstance(dept, dict) and dept.get("name"):
                departments.append(str(dept["name"]).strip())
        jobs.append(
            {
                "title": title,
                "url": url,
                "company": company,
                "location": location,
                "description": "" if lean else html_to_text(row.get("content") or ""),
                "posted_at": row.get("first_published") or row.get("updated_at"),
                "tags": departments[:6],
            }
        )
    return jobs


def _jobs_api_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "boards-api.greenhouse.io":
        path = parsed.path.rstrip("/")
        if not path.endswith("/jobs"):
            path = f"{path}/jobs"
        return urlunparse(("https", host, path, "", parsed.query, ""))
    match = _BOARD_RE.search(url)
    if match:
        return f"https://boards-api.greenhouse.io/v1/boards/{match.group(1)}/jobs"
    raise RuntimeError(f"greenhouse: untrusted API URL {url}")


def _with_content(api_url: str) -> str:
    parsed = urlparse(api_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["content"] = "true"
    return urlunparse(parsed._replace(query=urlencode(query)))
