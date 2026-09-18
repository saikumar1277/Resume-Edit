"""HTTPS JSON fetch with host allowlists, no redirects, no private IPs."""

from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

USER_AGENT = "resume-editor-jobs/1.0 (+https://localhost)"
DEFAULT_TIMEOUT_S = 30.0


class FetchError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status



class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FetchError(f"redirect blocked ({code})", status=code)


def _opener() -> urllib.request.OpenerDirector:
    # One opener per request: the shared opener is not thread-safe, and
    # concurrent scans were mixing board payloads (e.g. Stripe dropping out).
    return urllib.request.build_opener(_NoRedirect)


def assert_https_allowlist(url: str, allowed_hosts: set[str]) -> str:
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise FetchError(f"invalid URL: {url}") from exc
    if parsed.scheme != "https":
        raise FetchError(f"URL must use HTTPS: {url}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise FetchError(f"URL has no host: {url}")
    if host not in allowed_hosts:
        raise FetchError(f'untrusted hostname "{host}"')
    _assert_public_host(host)
    return url


def _assert_public_host(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError(f"DNS failed for {hostname}") from exc
    if not infos:
        raise FetchError(f"DNS returned no addresses for {hostname}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise FetchError(f"blocked non-public address {ip} for {hostname}")


def fetch_json(
    url: str,
    allowed_hosts: set[str],
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Any:
    href = assert_https_allowlist(url, allowed_hosts)
    request = urllib.request.Request(
        href,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    try:
        with _opener().open(request, timeout=timeout_s) as response:
            if getattr(response, "status", 200) != 200:
                raise FetchError(
                    f"HTTP {response.status} for {href}",
                    status=int(response.status),
                )
            raw = response.read()
    except FetchError:
        raise
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} for {href}", status=exc.code) from exc
    except TimeoutError as exc:
        raise FetchError(f"timeout fetching {href}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"network error fetching {href}: {exc.reason}") from exc
    except OSError as exc:
        raise FetchError(f"network error fetching {href}: {exc}") from exc

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchError(f"invalid JSON from {href}") from exc
