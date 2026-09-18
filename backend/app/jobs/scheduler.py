"""Run the ATS directory sweep every 6 hours. Never blocks GET /jobs."""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from . import store
from .sweep import INTERVAL_S, run_sweep

log = logging.getLogger(__name__)

INITIAL_DELAY_S = int(os.environ.get("JOBS_SWEEP_INITIAL_DELAY_S", "15"))
_stop = threading.Event()
_thread: threading.Thread | None = None


def start() -> None:
    global _thread
    if os.environ.get("JOBS_SWEEP_DISABLE") == "1":
        log.info("jobs sweep disabled")
        return
    store.init()
    store.mark_stale_running_failed()
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="jobs-sweep", daemon=True)
    _thread.start()
    log.info("jobs sweep thread starting")


def stop() -> None:
    _stop.set()


def _loop() -> None:
    while not _stop.is_set():
        wait_s = _seconds_until_next()
        store.set_next_run_at(_iso_from_now(wait_s))
        if _stop.wait(timeout=max(1.0, wait_s)):
            return
        limit = _limit_from_env()
        try:
            result = run_sweep(limit=limit)
        except Exception:
            log.exception("jobs sweep failed")
            if _stop.wait(timeout=60):
                return
            continue
        if result.get("skipped"):
            if _stop.wait(timeout=60):
                return


def _seconds_until_next() -> float:
    store.init()
    if store.job_count() == 0:
        return float(INITIAL_DELAY_S)
    meta = store.get_meta()
    due = _parse_time(meta.get("next_run_at")) or _plus_interval(meta.get("finished_at"))
    if due is None:
        return float(INTERVAL_S)
    wait = (due - datetime.now(timezone.utc)).total_seconds()
    return wait if wait > 1 else 1.0


def _plus_interval(finished_at: Any) -> datetime | None:
    parsed = _parse_time(finished_at)
    if parsed is None:
        return None
    return parsed + timedelta(seconds=INTERVAL_S)


def _parse_time(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso_from_now(seconds: float) -> str:
    when = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return when.isoformat().replace("+00:00", "Z")


def _limit_from_env() -> int | None:
    raw = os.environ.get("JOBS_SWEEP_LIMIT", "").strip()
    if not raw:
        return None
    try:
        return max(0, int(raw))
    except ValueError:
        return None
