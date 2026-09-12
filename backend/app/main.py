"""
FastAPI app: the HTTP layer around our PDF pipeline.

Four endpoints, matching the four things the UI needs to do:
  POST /resumes              upload a PDF, get back blocks JSON
  GET  /resumes/{id}         load that JSON for the editor
  PUT  /resumes/{id}         save editor changes
  GET  /resumes/{id}/download  turn current JSON back into a PDF
"""

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import json_store
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
    updated = json_store.update(resume_id, {"blocks": body.blocks})
    if updated is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return updated


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
