import type {
  Block,
  ChatMessage,
  ChatReply,
  Resume,
  ResumeSummary,
} from "./types";

const API = "/api";

export async function uploadPdf(file: File): Promise<Resume> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API}/resumes`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed.");
  }

  return res.json();
}

export async function getResume(id: string): Promise<Resume> {
  const res = await fetch(`${API}/resumes/${id}`);
  if (res.status === 404) {
    throw new Error("Resume not found.");
  }
  if (!res.ok) {
    throw new Error("Could not load resume.");
  }
  return res.json();
}

export async function searchResumes(query: string): Promise<ResumeSummary[]> {
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  const res = await fetch(`${API}/resumes?${params.toString()}`);
  if (!res.ok) {
    throw new Error("Could not search saved resumes.");
  }
  return res.json();
}

export async function deleteResume(id: string): Promise<void> {
  const res = await fetch(`${API}/resumes/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Delete failed.");
  }
}

export async function saveResume(
  id: string,
  blocks: Block[],
  note?: string,
): Promise<Resume> {
  const res = await fetch(`${API}/resumes/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      note === undefined ? { blocks } : { blocks, note },
    ),
  });
  if (!res.ok) {
    throw new Error("Save failed.");
  }
  return res.json();
}

/** Copy the current editor content into a new resume, so a download never
 *  overwrites the one being edited. The note is how it is found later. */
export async function snapshotResume(
  id: string,
  blocks: Block[],
  note: string,
): Promise<Resume> {
  const res = await fetch(`${API}/resumes/${id}/snapshot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blocks, note }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not save this download.");
  }
  return res.json();
}

/** Blocks are sent from the editor, not read from disk, so the assistant
 *  sees unsaved edits too. */
export async function chatWithResume(
  id: string,
  blocks: Block[],
  messages: ChatMessage[],
): Promise<ChatReply> {
  const res = await fetch(`${API}/resumes/${id}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blocks, messages }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "The assistant is unavailable.");
  }
  return res.json();
}

export async function downloadPdf(id: string, filename: string): Promise<void> {
  const res = await fetch(`${API}/resumes/${id}/download`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Download failed.");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
