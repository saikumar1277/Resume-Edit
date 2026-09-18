"""
FastAPI app: the HTTP layer around our PDF pipeline.

  GET    /health
  POST   /auth/signup
  POST   /auth/login
  POST   /auth/logout
  GET    /auth/me
  GET    /auth/providers
  POST   /auth/verify
  POST   /auth/resend-verify
  POST   /auth/forgot
  POST   /auth/reset
  GET    /auth/google
  GET    /auth/google/callback
  GET    /resumes
  POST   /resumes
  GET    /resumes/{id}
  PUT    /resumes/{id}
  DELETE /resumes/{id}
  POST   /resumes/{id}/snapshot
  POST   /resumes/{id}/chat
  GET    /resumes/{id}/download
  GET    /jobs
  GET    /jobs/status
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import ai, auth, google_oauth, mail, rate_limit, redis_client, resume_store
from .config import (
    APP_ENV,
    APP_PUBLIC_URL,
    CORS_ORIGINS,
    GOOGLE_ENABLED,
    MAX_UPLOAD_BYTES,
    SESSION_COOKIE,
)
from .db import get_db, ping_db
from .jobs import scheduler
from .jobs.scan import DEFAULT_LIMIT, MAX_LIMIT, list_jobs, sweep_status
from .jobs.store import init as init_jobs
from .migrate import upgrade_head
from .models import User
from .pipeline import ConvertError, convert_pdf, fit_to_one_page

log = logging.getLogger(__name__)


def _setup_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _setup_logging()
    log.info("starting app env=%s", APP_ENV)
    upgrade_head()
    init_jobs()
    scheduler.start()
    yield
    scheduler.stop()
    redis_client.reset_client()


app = FastAPI(title="Resume Editor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResumeUpdate(BaseModel):
    blocks: list[dict]
    note: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    blocks: list[dict]
    messages: list[ChatMessage]


class AuthBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class EmailBody(BaseModel):
    email: EmailStr


class TokenBody(BaseModel):
    token: str = Field(min_length=8, max_length=256)


class ResetBody(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    password: str = Field(min_length=8, max_length=128)


def _csv_values(raw: str, allowed: set[str], label: str) -> list[str]:
    values: list[str] = []
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if item not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid {label} filter.")
        if item not in values:
            values.append(item)
    return values


def _user_payload(user: User) -> dict:
    return {"id": str(user.id), "email": user.email}


@app.get("/health")
def health():
    db_ok = False
    redis_ok = False
    try:
        ping_db()
        db_ok = True
    except Exception:
        log.exception("health db failed")
    try:
        redis_client.ping_redis()
        redis_ok = True
    except Exception:
        log.exception("health redis failed")
    payload = {
        "ok": db_ok and redis_ok,
        "db": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
    return JSONResponse(payload, status_code=200 if payload["ok"] else 503)


@app.get("/auth/providers")
def auth_providers():
    return {"google": GOOGLE_ENABLED}


@app.post("/auth/signup")
def signup(
    body: AuthBody,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    rate_limit.enforce(request, "signup", 10)
    email = auth.normalize_email(str(body.email))
    user = User(
        email=email,
        password_hash=auth.hash_password(body.password),
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with that email already exists."
        ) from exc
    token = auth.create_session(db, user.id)
    auth.set_session_cookie(response, token)
    return _user_payload(user)


@app.post("/auth/login")
def login(
    body: AuthBody,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    rate_limit.enforce(request, "login", 10)
    email = auth.normalize_email(str(body.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not auth.verify_password(user.password_hash, body.password):
        log.info("login failed")
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = auth.create_session(db, user.id)
    auth.set_session_cookie(response, token)
    return _user_payload(user)


@app.post("/auth/verify")
def verify_email(body: TokenBody, response: Response, db: Session = Depends(get_db)):
    user_id = redis_client.take_token("verify", body.token)
    if not user_id:
        raise HTTPException(
            status_code=400, detail="This verification link is invalid or expired."
        )
    user = db.get(User, UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=400, detail="This verification link is invalid or expired."
        )
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
    token = auth.create_session(db, user.id)
    auth.set_session_cookie(response, token)
    return _user_payload(user)


@app.post("/auth/resend-verify")
def resend_verify(body: EmailBody, request: Request, db: Session = Depends(get_db)):
    rate_limit.enforce(request, "forgot", 10)
    email = auth.normalize_email(str(body.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is not None and user.email_verified_at is None and user.password_hash:
        mail.send_verify(user.id, user.email)
    return {"ok": True}


@app.post("/auth/forgot")
def forgot_password(body: EmailBody, request: Request, db: Session = Depends(get_db)):
    rate_limit.enforce(request, "forgot", 10)
    email = auth.normalize_email(str(body.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is not None and user.password_hash:
        mail.send_reset(user.id, user.email)
    return {"ok": True}


@app.post("/auth/reset")
def reset_password(body: ResetBody, response: Response, db: Session = Depends(get_db)):
    user_id = redis_client.take_token("reset", body.token)
    if not user_id:
        raise HTTPException(
            status_code=400, detail="This reset link is invalid or expired."
        )
    user = db.get(User, UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=400, detail="This reset link is invalid or expired."
        )
    user.password_hash = auth.hash_password(body.password)
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
    auth.revoke_sessions_for_user(db, user.id)
    token = auth.create_session(db, user.id)
    auth.set_session_cookie(response, token)
    return _user_payload(user)


@app.get("/auth/google")
def google_start(next: str = ""):
    try:
        url = google_oauth.authorization_url(next)
    except google_oauth.GoogleDisabledError as exc:
        raise HTTPException(
            status_code=503, detail="Google sign-in is not configured."
        ) from exc
    return RedirectResponse(url)


@app.get("/auth/google/callback")
def google_callback(
    db: Session = Depends(get_db),
    code: str = "",
    state: str = "",
    error: str = "",
):
    if error or not code or not state:
        return RedirectResponse(f"{APP_PUBLIC_URL}/login?error=google")
    try:
        user, next_path = google_oauth.finish(db, code, state)
    except google_oauth.GoogleAuthError:
        log.exception("google oauth failed")
        return RedirectResponse(f"{APP_PUBLIC_URL}/login?error=google")
    token = auth.create_session(db, user.id)
    redirect = RedirectResponse(f"{APP_PUBLIC_URL}{next_path}")
    auth.set_session_cookie(redirect, token)
    return redirect


@app.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth.revoke_session(db, request.cookies.get(SESSION_COOKIE))
    auth.clear_session_cookie(response)
    return {"ok": True}


@app.get("/auth/me")
def me(user: User = Depends(auth.get_current_user)):
    return _user_payload(user)


@app.get("/jobs")
def get_jobs(
    title: str = "",
    q: str = "",
    location: str = "",
    company: str = "",
    workplace: str = "",
    type: str = "",
    experience: str = "",
    posted: str = "",
    exclude: str = "",
    sort: str = "posted_desc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
):
    role = title.strip() or q.strip()
    workplaces = _csv_values(workplace, {"remote", "hybrid", "onsite"}, "workplace")
    job_types = _csv_values(
        type,
        {"full-time", "part-time", "contract", "internship"},
        "type",
    )
    levels = _csv_values(
        experience,
        {"intern", "entry", "mid", "senior"},
        "experience",
    )
    if posted and posted not in {"1d", "7d", "30d"}:
        raise HTTPException(status_code=400, detail="Invalid posted filter.")
    if sort not in {"posted_desc", "posted_asc", "company", "title"}:
        raise HTTPException(status_code=400, detail="Invalid sort.")
    if limit < 1 or limit > MAX_LIMIT:
        raise HTTPException(status_code=400, detail="Invalid limit.")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Invalid offset.")
    return list_jobs(
        title=role,
        location=location,
        company=company,
        workplaces=workplaces,
        job_types=job_types,
        experience=levels,
        posted=posted,
        exclude=exclude,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@app.get("/jobs/status")
def get_jobs_status():
    return sweep_status()


@app.get("/resumes")
def list_resumes(
    q: str = "",
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return resume_store.search(db, user.id, q)


@app.post("/resumes")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_BYTES + 64_000:
                raise HTTPException(
                    status_code=413, detail="PDF is too large (max 8 MB)."
                )
        except ValueError:
            pass
    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF is too large (max 8 MB).")
    try:
        resume = convert_pdf(pdf_bytes, file.filename)
    except ConvertError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resume_store.save_new(db, user.id, resume)


@app.get("/resumes/{resume_id}")
def get_resume(
    resume_id: str,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    resume = resume_store.load(db, user.id, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


@app.put("/resumes/{resume_id}")
def save_resume(
    resume_id: str,
    body: ResumeUpdate,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    payload = {"blocks": body.blocks}
    if body.note is not None:
        payload["note"] = body.note
    updated = resume_store.update(db, user.id, resume_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return updated


@app.delete("/resumes/{resume_id}")
def remove_resume(
    resume_id: str,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not resume_store.delete(db, user.id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {"deleted": resume_id}


@app.post("/resumes/{resume_id}/snapshot")
def snapshot_resume(
    resume_id: str,
    body: ResumeUpdate,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    source = resume_store.load(db, user.id, resume_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    snapshot = {
        "document": source.get("document"),
        "blocks": body.blocks,
        "note": body.note,
    }
    return resume_store.save_new(db, user.id, snapshot)


@app.post("/resumes/{resume_id}/chat")
def chat_about_resume(
    resume_id: str,
    body: ChatRequest,
    request: Request,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit.enforce(request, "chat", 20)
    if resume_store.load(db, user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    try:
        return ai.chat(body.blocks, [m.model_dump() for m in body.messages])
    except ai.AiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/resumes/{resume_id}/download")
def download_resume(
    resume_id: str,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    resume = resume_store.load(db, user.id, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if not resume.get("blocks"):
        raise HTTPException(
            status_code=400,
            detail="This resume has no paragraph data. Please upload the PDF again.",
        )
    pdf_bytes = fit_to_one_page(resume)
    filename = resume["document"].get("source_file", "resume.pdf")
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
