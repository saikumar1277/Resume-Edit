"""Walk ATS company directories and publish a Postgres snapshot when finished.

Full uncapped sweep (default): first run is typically 30–75 minutes (Ashby-bound).
Use --limit N to sample N slugs per ATS for local tests.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from . import store
from .http import FetchError
from .providers import PROVIDERS
from .scan import _load_portals, _resolve_provider

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ats"
LOCK_PATH = store.STORAGE_DIR / "jobs.sweep.lock"
INTERVAL_S = int(os.environ.get("JOBS_SWEEP_INTERVAL_S", str(6 * 3600)))
WORKERS = {
    "greenhouse": 30,
    "lever": 30,
    "ashby": 5,
}
CAREERS_URL = {
    "greenhouse": "https://boards.greenhouse.io/{slug}",
    "lever": "https://jobs.lever.co/{slug}",
    "ashby": "https://jobs.ashbyhq.com/{slug}",
}

_lock_fh = None


def run_sweep(limit: int | None = None) -> dict[str, Any]:
    store.init()
    if not _acquire_lock():
        return {"skipped": True, "reason": "another sweep is running"}
    started = time.monotonic()
    started_at = ""
    try:
        store.mark_stale_running_failed()
        started_at = store.begin_ingest()
        errors: list[str] = []
        counts: dict[str, int] = {}
        _run_platforms(limit, errors, counts)
        staged = store.staging_count()
        existing = store.job_count()
        if staged == 0 and existing > 0:
            store.abort("empty scrape; kept previous snapshot")
            return {
                "skipped": False,
                "ok": False,
                "reason": "empty scrape",
                "duration_s": round(time.monotonic() - started, 1),
                "counts": counts,
                "errors": errors[:20],
            }
        published = store.publish(
            started_at=started_at,
            errors=errors,
            counts=counts,
            interval_s=INTERVAL_S,
        )
        return {
            "skipped": False,
            "ok": True,
            "job_count": published,
            "duration_s": round(time.monotonic() - started, 1),
            "counts": counts,
            "errors": errors[:20],
        }
    except Exception as exc:
        store.abort(str(exc))
        raise
    finally:
        _release_lock()


def _run_platforms(
    limit: int | None,
    errors: list[str],
    counts: dict[str, int],
) -> None:
    work = [
        ("greenhouse", PROVIDERS["greenhouse"], _load_slugs("greenhouse", limit)),
        ("lever", PROVIDERS["lever"], _load_slugs("lever", limit)),
        ("ashby", PROVIDERS["ashby"], _load_slugs("ashby", limit)),
    ]
    with ThreadPoolExecutor(max_workers=len(work) + 1) as pool:
        futures = {
            pool.submit(_sweep_ats, provider_id, provider, slugs, errors): provider_id
            for provider_id, provider, slugs in work
        }
        futures[pool.submit(_sweep_job_boards, errors)] = "job_boards"
        for future in as_completed(futures):
            name = futures[future]
            counts[name] = future.result()


def _sweep_job_boards(errors: list[str]) -> int:
    config = _load_portals()
    inserted = 0
    for entry in config.get("job_boards") or []:
        if not isinstance(entry, dict):
            continue
        provider = _resolve_provider(entry)
        if provider is None:
            errors.append(f"{entry.get('name')}: no matching provider")
            continue
        label = str(entry.get("name") or provider.ID)
        try:
            rows = _lean_rows(provider.fetch(entry), provider.ID)
            inserted += store.insert_jobs(rows)
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    return inserted


def _sweep_ats(
    provider_id: str,
    provider: Any,
    slugs: list[str],
    errors: list[str],
) -> int:
    dead = store.load_dead_slugs(provider_id)
    live = [slug for slug in slugs if slug not in dead]
    workers = WORKERS.get(provider_id, 10)
    template = CAREERS_URL[provider_id]
    new_dead: dict[str, int | None] = {}
    inserted = 0
    error_budget = 0

    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(live)))) as pool:
        futures = {
            pool.submit(_fetch_slug, provider, provider_id, slug, template): slug
            for slug in live
        }
        for future in as_completed(futures):
            slug = futures[future]
            try:
                rows, status = future.result()
            except Exception as exc:
                if error_budget < 15:
                    errors.append(f"{provider_id}/{slug}: {exc}")
                    error_budget += 1
                continue
            if status in (404, 410):
                new_dead[slug] = status
                continue
            if rows:
                inserted += store.insert_jobs(rows)

    store.add_dead_slugs(provider_id, new_dead)
    return inserted


def _fetch_slug(
    provider: Any,
    provider_id: str,
    slug: str,
    template: str,
) -> tuple[list[dict[str, Any]], int | None]:
    if provider_id == "ashby":
        time.sleep(random.uniform(0.5, 2.0))
    entry = {"name": slug, "careers_url": template.format(slug=slug)}
    last_status: int | None = None
    for attempt in range(3):
        try:
            rows = provider.fetch(entry, lean=True)
            return _lean_rows(rows, provider_id), None
        except FetchError as exc:
            last_status = exc.status
            if exc.status in (429, 502, 503) and attempt < 2:
                time.sleep((2**attempt) + random.uniform(0.5, 1.5))
                continue
            if exc.status in (404, 410):
                return [], exc.status
            raise
    return [], last_status


def _lean_rows(rows: list[dict[str, Any]], provider_id: str) -> list[dict[str, Any]]:
    scraped_at = _scraped_now()
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item["description"] = ""
        item["provider"] = provider_id
        item["scraped_at"] = scraped_at
        out.append(item)
    return out


def _scraped_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_slugs(provider_id: str, limit: int | None) -> list[str]:
    path = DATA_DIR / f"{provider_id}_companies.json"
    if not path.exists():
        raise RuntimeError(f"missing slug list: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise RuntimeError(f"{path} must be a JSON array")
    slugs = [str(item).strip() for item in loaded if str(item).strip()]
    if limit is not None:
        return slugs[: max(0, limit)]
    return slugs


def _acquire_lock() -> bool:
    global _lock_fh
    import fcntl

    store.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK_PATH, "a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return False
    _lock_fh = handle
    return True


def _release_lock() -> None:
    global _lock_fh
    import fcntl

    handle = _lock_fh
    _lock_fh = None
    if handle is None:
        return
    try:
        fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        handle.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Greenhouse/Lever/Ashby directories into Postgres. "
            "Default is the full list (30–75 min first run). "
            "Pass --limit N for a short local sample."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max company slugs per ATS (omit for the full directory).",
    )
    args = parser.parse_args(argv)
    result = run_sweep(limit=args.limit)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") or result.get("skipped") else 1


if __name__ == "__main__":
    sys.exit(main())
