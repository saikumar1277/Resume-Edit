"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import { FontSize, TextStyle } from "@tiptap/extension-text-style";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { downloadPdf, getResume, saveResume } from "../../../lib/api";
import { blocksToTiptap, tiptapToBlocks } from "../../../lib/tiptapDoc";
import { ResumeDivider, ResumeParagraph } from "../../../lib/tiptapExtensions";
import type { Resume } from "../../../lib/types";

const editorExtensions = [
  StarterKit.configure({
    heading: false,
    bulletList: false,
    orderedList: false,
    listItem: false,
    listKeymap: false,
    blockquote: false,
    codeBlock: false,
    code: false,
    horizontalRule: false,
    paragraph: false,
  }),
  ResumeParagraph,
  ResumeDivider,
  TextStyle,
  Color,
  FontFamily,
  FontSize,
];

export default function Editor({ resumeId }: { resumeId: string }) {
  const [resume, setResume] = useState<Resume | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const editor = useEditor({
    extensions: editorExtensions,
    content: { type: "doc", content: [] },
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "resume-doc",
      },
    },
  });

  useEffect(() => {
    getResume(resumeId)
      .then((data) => {
        if (!data.blocks) {
          throw new Error(
            "This resume is missing paragraph data. Please upload the PDF again.",
          );
        }
        setResume(data);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Load failed."),
      );
  }, [resumeId]);

  useEffect(() => {
    if (!editor || !resume) return;
    editor.commands.setContent(blocksToTiptap(resume.blocks));
  }, [editor, resume?.id]);

  const [, setToolbarTick] = useState(0);
  useEffect(() => {
    if (!editor) return;
    const refresh = () => setToolbarTick((n) => n + 1);
    editor.on("selectionUpdate", refresh);
    editor.on("transaction", refresh);
    return () => {
      editor.off("selectionUpdate", refresh);
      editor.off("transaction", refresh);
    };
  }, [editor]);

  async function persist(): Promise<Resume | null> {
    if (!resume || !editor) return null;
    const blocks = tiptapToBlocks(editor.getJSON());
    const saved = await saveResume(resume.id, blocks);
    setResume(saved);
    return saved;
  }

  async function onSave() {
    setStatus("Saving…");
    try {
      await persist();
      setStatus("Saved.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Save failed.");
    }
  }

  async function onDownload() {
    if (!resume) return;
    setStatus("Saving…");
    try {
      const saved = await persist();
      if (!saved) return;
      setStatus("Building PDF…");
      await downloadPdf(saved.id, saved.document.source_file || "resume.pdf");
      setStatus("Downloaded.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Download failed.");
    }
  }

  if (error) {
    return (
      <main className="px-6 py-16">
        <p className="text-red-600">{error}</p>
        <Link href="/" className="mt-4 inline-block text-sm underline">
          Back to upload
        </Link>
      </main>
    );
  }

  if (!resume) {
    return <p className="px-6 py-16 text-sm">Loading…</p>;
  }

  const { width, height } = resume.document.page_size_pt;
  const margins = resume.document.margins_pt ?? {
    left: 28,
    right: 22,
    top: 18,
    bottom: 18,
  };

  return (
    <div className="editor-shell">
      <header className="no-print sticky top-0 z-10 flex items-center gap-3 border-b bg-white px-4 py-3">
        <Link href="/" className="text-sm underline">
          New upload
        </Link>
        <button
          type="button"
          onClick={() => editor?.chain().focus().toggleBold().run()}
          className={`rounded border px-3 py-1.5 text-sm ${
            editor?.isActive("bold") ? "bg-neutral-900 text-white" : ""
          }`}
        >
          Bold
        </button>
        <button
          type="button"
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          className={`rounded border px-3 py-1.5 text-sm ${
            editor?.isActive("italic") ? "bg-neutral-900 text-white" : ""
          }`}
        >
          Italic
        </button>
        <button
          type="button"
          onClick={onSave}
          className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white"
        >
          Save
        </button>
        <button
          type="button"
          onClick={onDownload}
          className="rounded border px-3 py-1.5 text-sm"
        >
          Download PDF
        </button>
        <span className="text-sm text-neutral-500">{status}</span>
      </header>

      <div
        className="resume-canvas"
        style={{
          width: `${width}pt`,
          minHeight: `${height}pt`,
          padding: `${margins.top}pt ${margins.right}pt ${margins.bottom}pt ${margins.left}pt`,
        }}
      >
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
