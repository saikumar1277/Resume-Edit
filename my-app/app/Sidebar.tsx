"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { deleteResume, searchResumes, uploadPdf } from "../lib/api";
import type { ResumeSummary } from "../lib/types";

/**
 * Concept: overlay + search.
 * Open state lives in the parent (toolbar). This panel only renders
 * when open, and searches stored resume notes as the user types.
 */
export default function Sidebar({
  open,
  onClose,
  fileName,
  currentId,
}: {
  open: boolean;
  onClose: () => void;
  fileName?: string;
  currentId?: string;
}) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ResumeSummary[]>([]);
  const [searchError, setSearchError] = useState("");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    searchResumes(query)
      .then((items) => {
        if (!cancelled) {
          setResults(items);
          setSearchError("");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setSearchError(err instanceof Error ? err.message : "Search failed.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, query]);

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setError("");
    setBusy(true);
    try {
      const resume = await uploadPdf(file);
      onClose();
      router.push(`/editor/${resume.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  function openResume(id: string) {
    onClose();
    router.push(`/editor/${id}`);
  }

  async function onDelete(item: ResumeSummary) {
    const label = item.note || item.source_file || "this resume";
    if (!window.confirm(`Delete ${label}? This cannot be undone.`)) return;

    setSearchError("");
    try {
      await deleteResume(item.id);
      setResults((items) => items.filter((entry) => entry.id !== item.id));
      // The editor behind this panel would 404 on the next load.
      if (item.id === currentId) {
        onClose();
        router.push("/");
      }
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        className="app-sidebar-backdrop"
        aria-label="Close menu"
        onClick={onClose}
      />
      <aside className="app-sidebar-layer">
        <p className="app-sidebar-title">Resume editor</p>
        {fileName ? (
          <p className="app-sidebar-file" title={fileName}>
            {fileName}
          </p>
        ) : null}

        <label className={`app-sidebar-upload ${busy ? "is-busy" : ""}`}>
          <span>{busy ? "Converting…" : "Upload PDF"}</span>
          <input
            type="file"
            accept="application/pdf"
            disabled={busy}
            onChange={onFileChange}
          />
        </label>
        {error ? <p className="app-sidebar-error">{error}</p> : null}

        <input
          type="search"
          className="app-sidebar-search"
          placeholder="Search by note"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Search saved resumes by note"
        />
        {searchError ? (
          <p className="app-sidebar-error">{searchError}</p>
        ) : null}

        {results.length === 0 ? (
          <p className="app-sidebar-empty">No saved resumes match</p>
        ) : (
          <ul className="app-sidebar-results">
            {results.map((item, index) => (
              <li
                className="app-sidebar-row"
                key={item.id || `${item.source_file}-${index}`}
              >
                <button
                  type="button"
                  className="app-sidebar-result"
                  onClick={() => openResume(item.id)}
                >
                  <span className="app-sidebar-result-note">
                    {item.note || "No note"}
                  </span>
                  <span className="app-sidebar-result-file">
                    {item.source_file || "Untitled"}
                  </span>
                </button>
                <button
                  type="button"
                  className="app-sidebar-delete"
                  title="Delete"
                  aria-label={`Delete ${item.note || item.source_file}`}
                  onClick={() => onDelete(item)}
                >
                  <TrashIcon />
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
    </>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path
        fill="currentColor"
        d="M9 3h6l1 2h4v2H4V5h4l1-2zM6 9h12l-1 11a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L6 9zm3 2v9h2v-9H9zm4 0v9h2v-9h-2z"
      />
    </svg>
  );
}
