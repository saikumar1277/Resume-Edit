"""
FastAPI app: the HTTP layer around our PDF pipeline.

The HTTP surface, matching what the UI needs to do:
  GET    /resumes              list/search saved resumes by note
  POST   /resumes              upload a PDF, get back blocks JSON
  GET    /resumes/{id}         load that JSON for the editor
  PUT    /resumes/{id}         save editor changes
  DELETE /resumes/{id}         drop a saved resume
  POST   /resumes/{id}/snapshot  copy current blocks + note to a new resume
  POST   /resumes/{id}/chat      ask the assistant for edits to those blocks
  GET    /resumes/{id}/download  turn current JSON back into a PDF
"""

from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import ai, json_store
from .pipeline import ConvertError, convert_pdf, fit_to_one_page

app = FastAPI(title="Resume Editor API")

# Next.js runs on :3000, this API on :8000. Browsers block that by default
# (CORS). Allowing localhost:3000 lets the frontend call us directly.
# We also proxy /api/* through Next.js — either path works.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


@app.get("/resumes")
def list_resumes(q: str = ""):
    return json_store.search(q)


@app.post("/resumes")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    pdf_bytes = await file.read()
    try:
        resume = convert_pdf(pdf_bytes, file.filename)
    except ConvertError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    saved = json_store.save_new(resume)
    return saved


@app.get("/resumes/{resume_id}")
def get_resume(resume_id: str):
    resume = json_store.load(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


@app.put("/resumes/{resume_id}")
def save_resume(resume_id: str, body: ResumeUpdate):
    payload = {"blocks": body.blocks}
    if body.note is not None:
        payload["note"] = body.note
    updated = json_store.update(resume_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return updated


@app.delete("/resumes/{resume_id}")
def remove_resume(resume_id: str):
    if not json_store.delete(resume_id):
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {"deleted": resume_id}


@app.post("/resumes/{resume_id}/snapshot")
def snapshot_resume(resume_id: str, body: ResumeUpdate):
    source = json_store.load(resume_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Resume not found.")

    snapshot = {
        "document": source.get("document"),
        "blocks": body.blocks,
        "note": body.note,
    }
    return json_store.save_new(snapshot)


@app.post("/resumes/{resume_id}/chat")
def chat_about_resume(resume_id: str, body: ChatRequest):
    if json_store.load(resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")

    # Blocks come from the request, not from disk, so the assistant sees
    # what is on screen right now including unsaved edits.
    try:
        return ai.chat(body.blocks, [m.model_dump() for m in body.messages])
    except ai.AiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/resumes/{resume_id}/download")
def download_resume(resume_id: str):
    resume = json_store.load(resume_id)
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
