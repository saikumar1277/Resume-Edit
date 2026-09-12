"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadPdf } from "../lib/api";

export default function Home() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setError("");
    setBusy(true);
    try {
      const resume = await uploadPdf(file);
      router.push(`/editor/${resume.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <h1 className="text-2xl font-semibold">Resume editor</h1>
      <p className="mt-2 text-sm text-neutral-600">
        Upload a PDF. We turn it into editable paragraphs, then you can
        type like a document and download a reflowed PDF.
      </p>

      <label className="mt-8 flex cursor-pointer flex-col items-center rounded-lg border border-dashed border-neutral-300 px-6 py-10 text-center hover:border-neutral-500">
        <span className="text-sm font-medium">
          {busy ? "Converting…" : "Choose a PDF"}
        </span>
        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          disabled={busy}
          onChange={onFileChange}
        />
      </label>

      {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
    </main>
  );
}
