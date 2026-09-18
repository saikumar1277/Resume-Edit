"""Map provider rows onto the frontend Job shape."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

JobWorkplace = Literal["remote", "hybrid", "onsite"]
JobType = Literal["full-time", "part-time", "contract", "internship"]
JobExperience = Literal["intern", "entry", "mid", "senior"]

_REMOTE_RE = re.compile(
    r"\bremote\b|distributed|work from home|wfh|anywhere\b",
    re.IGNORECASE,
)
_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)
_INTERN_RE = re.compile(r"\bintern(?:ship)?s?\b", re.IGNORECASE)
_CONTRACT_RE = re.compile(r"\bcontract(?:or|ing)?\b|freelance", re.IGNORECASE)
_PART_RE = re.compile(r"part[-\s]?time", re.IGNORECASE)
_FULL_RE = re.compile(r"full[-\s]?time", re.IGNORECASE)

_TYPE_ALIASES = {
    "full_time": "full-time",
    "full-time": "full-time",
    "fulltime": "full-time",
    "part_time": "part-time",
    "part-time": "part-time",
    "parttime": "part-time",
    "contract": "contract",
    "contractor": "contract",
    "freelance": "contract",
    "temporary": "contract",
    "internship": "internship",
    "intern": "internship",
}


def job_id_for(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return digest[:16]


def posted_iso(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        ms = float(value)
        if ms > 10_000_000_000:
            ms /= 1000
        try:
            return datetime.fromtimestamp(ms, tz=timezone.utc).date().isoformat()
        except (OSError, OverflowError, ValueError):
            return ""
    text = str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError:
        match = re.match(r"(\d{4}-\d{2}-\d{2})", text)
        return match.group(1) if match else ""


def infer_workplace(
    *parts: object,
    default: JobWorkplace = "onsite",
) -> JobWorkplace:
    blob = " ".join(_as_text(part) for part in parts)
    if _HYBRID_RE.search(blob):
        return "hybrid"
    if _REMOTE_RE.search(blob):
        return "remote"
    return default


def infer_type(*parts: object, default: JobType = "full-time") -> JobType:
    blob = " ".join(_as_text(part) for part in parts)
    for part in parts:
        aliased = _TYPE_ALIASES.get(_as_text(part).lower().replace(" ", "_"))
        if aliased:
            return aliased  # type: ignore[return-value]
    if _INTERN_RE.search(blob):
        return "internship"
    if _CONTRACT_RE.search(blob):
        return "contract"
    if _PART_RE.search(blob):
        return "part-time"
    if _FULL_RE.search(blob):
        return "full-time"
    return default


_TIER_PATTERNS = [
    (re.compile(r"\b(?:chief|cto|ceo|cfo|vp|vice president|director)\b"), 50),
    (re.compile(r"\b(?:principal|distinguished|fellow)\b"), 40),
    (re.compile(r"\b(?:staff|lead|head of)\b"), 30),
    (re.compile(r"\b(?:senior|sr\.?)\b"), 20),
    (re.compile(r"\b(?:architect|manager)\b"), 15),
    (re.compile(r"\b(?:iii|iv|v|vi)\b"), 15),
    (re.compile(r"\blevel\s*[4-9]\b"), 15),
    (re.compile(r"\bengr?\s*[4-6]\b"), 15),
    (re.compile(r"\b(?:counsel|of\s*counsel)\b"), 20),
    (re.compile(r"\b(?:attending|charge)\b"), 20),
    (re.compile(r"\b(?:ii|2)\b"), 5),
    (re.compile(r"\blevel\s*3\b"), 5),
    (re.compile(r"\b(?:associate)\b"), -10),
    (re.compile(r"\b(?:junior|jr\.?)\b"), -20),
    (re.compile(r"\bentry[\s-]?level\b"), -25),
    (re.compile(r"\b(?:i|1)\b(?!\s*-|\d)"), -15),
    (re.compile(r"\b(?:trainee|graduate|new\s*grad)\b"), -25),
    (re.compile(r"\b(?:paralegal|clerk)\b"), -15),
    (re.compile(r"\b(?:resident|clinical\s*fellow)\b"), -15),
    (re.compile(r"\b(?:aide|assistant|tech)\b"), -10),
    (re.compile(r"\bintern(?:ship)?\b"), -100),
]


def experience_level(title: object) -> JobExperience:
    title_lower = _as_text(title).lower()
    score = 0
    for pattern, weight in _TIER_PATTERNS:
        if pattern.search(title_lower):
            score += weight
    if score <= -50:
        return "intern"
    if score <= -5:
        return "entry"
    if score >= 15:
        return "senior"
    return "mid"


def to_job(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = _as_text(raw.get("title"))
    url = _as_text(raw.get("url"))
    if not title or not url or not re.match(r"https?://", url, re.IGNORECASE):
        return None
    location = _as_text(raw.get("location"))
    description = _as_text(raw.get("description"))
    tags = [
        tag
        for tag in raw.get("tags") or []
        if isinstance(tag, str) and tag.strip()
    ][:8]
    workplace = raw.get("workplace")
    if workplace not in {"remote", "hybrid", "onsite"}:
        workplace = infer_workplace(
            location,
            description[:400],
            default=raw.get("workplace_default") or "onsite",
        )
    job_type = raw.get("type")
    if job_type not in {"full-time", "part-time", "contract", "internship"}:
        job_type = infer_type(title, raw.get("raw_type"), description[:400])
    return {
        "id": job_id_for(url),
        "title": title,
        "company": _as_text(raw.get("company")) or "Unknown",
        "location": location or "Location not listed",
        "workplace": workplace,
        "type": job_type,
        "postedAt": posted_iso(raw.get("posted_at")),
        "description": description,
        "tags": tags,
        "url": url,
        "experience": experience_level(title),
    }


_POSTED_DAYS = {"1d": 1, "7d": 7, "30d": 30}


def filter_jobs(
    jobs: list[dict[str, Any]],
    title: str = "",
    location: str = "",
    company: str = "",
    workplaces: list[str] | None = None,
    job_types: list[str] | None = None,
    experience: list[str] | None = None,
    posted: str = "",
    exclude: str = "",
    sort: str = "posted_desc",
) -> list[dict[str, Any]]:
    needle = title.strip().lower()
    place = location.strip().lower()
    company_needle = company.strip().lower()
    excluded = [part.lower() for part in re.split(r"[\s,]+", exclude.strip()) if part]
    cutoff = ""
    days = _POSTED_DAYS.get(posted)
    if days:
        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    out: list[dict[str, Any]] = []
    for job in jobs:
        job_title = (job.get("title") or "").lower()
        if needle and needle not in job_title:
            continue
        if place and place not in (job.get("location") or "").lower():
            continue
        if company_needle and company_needle not in (job.get("company") or "").lower():
            continue
        if workplaces and job.get("workplace") not in workplaces:
            continue
        if job_types and job.get("type") not in job_types:
            continue
        level = job.get("experience") or experience_level(job.get("title"))
        if experience and level not in experience:
            continue
        posted_at = job.get("postedAt") or ""
        if cutoff and (not posted_at or posted_at < cutoff):
            continue
        blob = f"{job.get('title') or ''} {job.get('company') or ''}".lower()
        if any(token in blob for token in excluded):
            continue
        if "experience" not in job:
            job = {**job, "experience": level}
        out.append(job)
    reverse_posted = sort != "posted_asc"
    if sort == "company":
        out.sort(key=lambda row: (row.get("company") or "").lower())
    elif sort == "title":
        out.sort(key=lambda row: (row.get("title") or "").lower())
    else:
        out.sort(key=lambda row: row.get("postedAt") or "", reverse=reverse_posted)
    return out


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
