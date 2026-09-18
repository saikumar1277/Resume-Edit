"""Serve jobs from the Postgres snapshot, with a live portals.yml bootstrap."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from . import store
from .http import FetchError
from .normalize import filter_jobs, to_job
from .providers import ATS_PROVIDERS, PROVIDERS

PORTALS_PATH = Path(__file__).resolve().parent.parent.parent / "portals.yml"
CACHE_TTL_S = 10 * 60
MAX_LIVE_JOBS = 2500
DEFAULT_LIMIT = 50
MAX_LIMIT = 200

_cache_lock = threading.Lock()
_scan_lock = threading.Lock()
_cache: tuple[float, list[dict[str, Any]], list[str]] | None = None


def list_jobs(
    title: str = "",
    location: str = "",
    company: str = "",
    workplaces: list[str] | None = None,
    job_types: list[str] | None = None,
    experience: list[str] | None = None,
    posted: str = "",
    exclude: str = "",
    sort: str = "posted_desc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    meta = store.get_meta()
    sweep = _sweep_payload(meta)
    if store.job_count() > 0:
        jobs, total = store.search(
            title=title,
            location=location,
            company=company,
            workplaces=workplaces,
            job_types=job_types,
            experience=experience,
            posted=posted,
            exclude=exclude,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    else:
        jobs, total = [], 0
    return {
        "jobs": jobs,
        "total": total,
        "source": "snapshot",
        "errors": [],
        "updated_at": meta.get("finished_at"),
        "sweep": sweep,
    }


def sweep_status() -> dict[str, Any]:
    meta = store.get_meta()
    return {
        "total": store.job_count(),
        "updated_at": meta.get("finished_at"),
        "sweep": _sweep_payload(meta),
    }


def _sweep_payload(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": meta.get("status") or "idle",
        "started_at": meta.get("started_at"),
        "finished_at": meta.get("finished_at"),
        "duration_s": meta.get("duration_s"),
        "job_count": meta.get("job_count") or 0,
        "next_run_at": meta.get("next_run_at"),
        "counts": meta.get("counts") or {},
        "errors": meta.get("error_sample") or [],
    }


def _cached_scan() -> tuple[list[dict[str, Any]], list[str]]:
    global _cache
    now = time.monotonic()
    with _cache_lock:
        if _cache and now - _cache[0] < CACHE_TTL_S:
            return _cache[1], _cache[2]
    with _scan_lock:
        now = time.monotonic()
        with _cache_lock:
            if _cache and now - _cache[0] < CACHE_TTL_S:
                return _cache[1], _cache[2]
        jobs, errors = scan()
        with _cache_lock:
            _cache = (time.monotonic(), jobs, errors)
        return jobs, errors


def scan() -> tuple[list[dict[str, Any]], list[str]]:
    config = _load_portals()
    entries = [
        *(config.get("job_boards") or []),
        *(config.get("tracked_companies") or []),
    ]
    errors: list[str] = []
    raw_rows: list[dict[str, Any]] = []

    work: list[tuple[str, Any, dict[str, Any]]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        provider = _resolve_provider(entry)
        if provider is None:
            name = entry.get("name") or entry.get("careers_url") or "entry"
            errors.append(f"{name}: no matching provider")
            continue
        work.append((provider.ID, provider, entry))

    if not work:
        return [], errors

    with ThreadPoolExecutor(max_workers=min(10, len(work))) as pool:
        futures = {
            pool.submit(_fetch_entry, provider, entry): (provider_id, entry)
            for provider_id, provider, entry in work
        }
        for future in as_completed(futures):
            provider_id, entry = futures[future]
            label = entry.get("name") or provider_id
            try:
                raw_rows.extend(future.result())
            except Exception as exc:
                errors.append(f"{label}: {exc}")

    seen: set[str] = set()
    jobs: list[dict[str, Any]] = []
    for raw in raw_rows:
        job = to_job(raw)
        if job is None:
            continue
        key = job["url"].rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        jobs.append(job)
    jobs.sort(key=lambda row: row.get("postedAt") or "", reverse=True)
    return jobs[:MAX_LIVE_JOBS], errors


def _fetch_entry(provider: Any, entry: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return provider.fetch(entry)
    except FetchError:
        raise
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def _resolve_provider(entry: dict[str, Any]):
    explicit = str(entry.get("provider") or "").strip()
    if explicit:
        return PROVIDERS.get(explicit)
    for provider in ATS_PROVIDERS:
        if provider.detect(entry):
            return provider
    return None


def _load_portals() -> dict[str, Any]:
    if not PORTALS_PATH.exists():
        return {
            "job_boards": [{"name": "Remotive", "provider": "remotive"}],
            "tracked_companies": [],
        }
    loaded = yaml.safe_load(PORTALS_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise RuntimeError("portals.yml must be a mapping")
    return loaded
