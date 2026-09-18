from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app import mail
from app.jobs import scan


def _token_from_url(url: str | None) -> str:
    assert url
    return parse_qs(urlparse(url).query)["token"][0]


def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["db"] == "ok"
    assert body["redis"] == "ok"


def test_signup_sets_session_and_login(client):
    signup = client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": "password12"},
    )
    assert signup.status_code == 200
    assert signup.json()["email"] == "new@example.com"
    assert "session" in signup.cookies
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"

    client.cookies.clear()
    login = client.post(
        "/auth/login",
        json={"email": "new@example.com", "password": "password12"},
    )
    assert login.status_code == 200
    assert "session" in login.cookies


def test_forgot_reset_revokes_old_session(client):
    client.post(
        "/auth/signup",
        json={"email": "reset@example.com", "password": "password12"},
    )
    old = client.cookies.get("session")
    assert old

    forgot = client.post("/auth/forgot", json={"email": "reset@example.com"})
    assert forgot.status_code == 200
    reset = client.post(
        "/auth/reset",
        json={
            "token": _token_from_url(mail.last_reset_url),
            "password": "password99",
        },
    )
    assert reset.status_code == 200
    client.cookies.clear()
    stale = client.get("/auth/me", cookies={"session": old})
    assert stale.status_code == 401
    fresh = client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "password99"},
    )
    assert fresh.status_code == 200


def test_resumes_require_auth(client):
    assert client.get("/resumes").status_code == 401


def test_empty_jobs_snapshot_no_live_ats(monkeypatch):
    monkeypatch.setattr(scan.store, "job_count", lambda: 0)
    monkeypatch.setattr(
        scan.store,
        "get_meta",
        lambda: {
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_s": None,
            "job_count": 0,
            "error_sample": [],
            "next_run_at": None,
            "counts": {},
        },
    )
    called = {"scan": False}
    monkeypatch.setattr(
        scan, "_cached_scan", lambda: called.__setitem__("scan", True) or ([], [])
    )
    result = scan.list_jobs()
    assert result["total"] == 0
    assert result["jobs"] == []
    assert result["source"] == "snapshot"
    assert called["scan"] is False


def test_google_disabled(client):
    providers = client.get("/auth/providers")
    assert providers.status_code == 200
    assert providers.json() == {"google": False}
    start = client.get("/auth/google", follow_redirects=False)
    assert start.status_code == 503


def test_google_callback_sets_session(client, monkeypatch):
    from app import google_oauth, redis_client

    monkeypatch.setattr(
        google_oauth,
        "fetch_google_profile",
        lambda code: {
            "email": "google@example.com",
            "id": "google-sub-1",
            "verified_email": True,
        },
    )
    redis_client.put_json("oauth", "state-token", {"next": "/resumes"}, 600)
    res = client.get(
        "/auth/google/callback?code=abc&state=state-token",
        follow_redirects=False,
    )
    assert res.status_code in {302, 303, 307}
    assert "session" in res.cookies
    client.cookies.set("session", res.cookies["session"])
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "google@example.com"
