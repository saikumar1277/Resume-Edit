"""Turn ATS HTML bodies into plain text (career-ops htmlToText, simplified)."""

from __future__ import annotations

import html
import re

DESCRIPTION_CAP = 2000

_HTML_MEDIA_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE = re.compile(r"<(?:[^>\"']|\"[^\"]*\"|'[^']*')+>")


def html_to_text(content: object) -> str:
    if not isinstance(content, str) or not content:
        return ""
    decoded = html.unescape(_strip_markup(content))
    decoded = html.unescape(_strip_markup(decoded))
    text = _strip_markup(decoded)
    text = re.sub(r"<(?=/[a-z!?])", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:DESCRIPTION_CAP]


def _strip_markup(content: str) -> str:
    return _HTML_TAG_RE.sub(" ", _HTML_MEDIA_RE.sub(" ", content))
