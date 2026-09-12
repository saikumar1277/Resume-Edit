import type { Block, Resume } from "./types";

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

export async function saveResume(
  id: string,
  blocks: Block[],
): Promise<Resume> {
  const res = await fetch(`${API}/resumes/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blocks }),
  });
  if (!res.ok) {
    throw new Error("Save failed.");
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
