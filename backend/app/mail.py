"""Transactional email via Resend, or the log in development."""

from __future__ import annotations

import logging
import secrets
from uuid import UUID

import httpx

from . import redis_client
from .config import (
    APP_PUBLIC_URL,
    EMAIL_FROM,
    RESEND_API_KEY,
    RESET_TTL_S,
    VERIFY_TTL_S,
)

log = logging.getLogger(__name__)

last_verify_url: str | None = None
last_reset_url: str | None = None
payloads: list[dict[str, str]] = []


def send_verify(user_id: UUID, email: str) -> str:
    token = secrets.token_urlsafe(32)
    redis_client.put_token("verify", token, str(user_id), VERIFY_TTL_S)
    url = f"{APP_PUBLIC_URL}/verify?token={token}"
    text = "Confirm your email by opening this link:\n" + url + "\n"
    html = f'<p>Confirm your email:</p><p><a href="{url}">{url}</a></p>'
    _deliver(email, "Verify your Page one account", text, html)
    global last_verify_url
    last_verify_url = url
    return url


def send_reset(user_id: UUID, email: str) -> str:
    token = secrets.token_urlsafe(32)
    redis_client.put_token("reset", token, str(user_id), RESET_TTL_S)
    url = f"{APP_PUBLIC_URL}/reset?token={token}"
    text = "Reset your password by opening this link:\n" + url + "\n"
    html = f'<p>Reset your password:</p><p><a href="{url}">{url}</a></p>'
    _deliver(email, "Reset your Page one password", text, html)
    global last_reset_url
    last_reset_url = url
    return url


def _deliver(to: str, subject: str, text: str, html: str) -> None:
    payloads.append({"to": to, "subject": subject, "text": text})
    if not RESEND_API_KEY:
        log.info("mail %s -> %s\n%s", subject, to, text)
        return
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "text": text,
            "html": html,
        },
        timeout=15.0,
    )
    if response.status_code >= 400:
        log.error("resend failed %s %s", response.status_code, response.text)
        raise RuntimeError("Could not send email.")
