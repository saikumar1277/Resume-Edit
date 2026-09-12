"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import TextAlign from "@tiptap/extension-text-align";
import { FontSize, TextStyle } from "@tiptap/extension-text-style";
import Underline from "@tiptap/extension-underline";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Sidebar from "../../Sidebar";
import {
  downloadPdf,
  getResume,
  saveResume,
  snapshotResume,
} from "../../../lib/api";
import {
  blocksToTiptap,
  boldMarkedTextNodes,
  dominantRun,
  tiptapToBlocks,
} from "../../../lib/tiptapDoc";
import { ResumeDivider, ResumeParagraph } from "../../../lib/tiptapExtensions";
import type { Block, ResumeEdit, Resume } from "../../../lib/types";
import ChatPanel from "./ChatPanel";
import Toolbar from "./Toolbar";

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
  Underline,
  TextAlign.configure({ types: ["paragraph"] }),
];

export default function Editor({ resumeId }: { resumeId: string }) {
  const [resume, setResume] = useState<Resume | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteDraft, setNoteDraft] = useState("");

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
    setError("");
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

  function currentBlocks(): Block[] {
    return editor ? tiptapToBlocks(editor.getJSON()) : [];
  }

  function blockText(blockId: string): string {
    const block = currentBlocks().find((item) => item.id === blockId);
    if (!block || block.type === "divider") return "";
    return block.runs.map((run) => run.text).join("");
  }

  /** Apply one assistant suggestion to the document. Edits land in the
   *  editor only, so Save, Download and Undo all keep working as before. */
  function applyEdit(edit: ResumeEdit): boolean {
    if (!editor) return false;

    const hits: { pos: number; size: number }[] = [];
    editor.state.doc.descendants((node, pos) => {
      if (hits.length === 0 && node.attrs?.blockId === edit.block_id) {
        hits.push({ pos, size: node.nodeSize });
      }
      return hits.length === 0;
    });
    const hit = hits[0];
    if (!hit) return false;

    const source = currentBlocks().find((item) => item.id === edit.block_id);
    const nodes = boldMarkedTextNodes(edit.text, dominantRun(source));

    if (edit.op === "insert_after") {
      editor
        .chain()
        .focus()
        .insertContentAt(hit.pos + hit.size, {
          type: "paragraph",
          attrs: {
            blockId: `b-${crypto.randomUUID().slice(0, 8)}`,
            blockType: "paragraph",
            textAlign:
              source && source.type !== "divider" ? source.align : "left",
          },
          content: nodes,
        })
        .run();
      return true;
    }

    // Replace only the inline content, so the paragraph node and its
    // blockId/blockType attributes survive the edit.
    editor
      .chain()
      .focus()
      .insertContentAt({ from: hit.pos + 1, to: hit.pos + hit.size - 1 }, nodes)
      .run();
    return true;
  }

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

  function onDownload() {
    if (!resume) return;
    setNoteDraft(resume.note || "");
    setNoteOpen(true);
  }

  async function confirmDownload(event: FormEvent) {
    event.preventDefault();
    if (!resume || !editor) return;
    setNoteOpen(false);
    setStatus("Saving…");
    try {
      const blocks = tiptapToBlocks(editor.getJSON());
      const snapshot = await snapshotResume(resume.id, blocks, noteDraft);
      setStatus("Building PDF…");
      await downloadPdf(
        snapshot.id,
        snapshot.document.source_file || "resume.pdf",
      );
      setStatus("Downloaded.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Download failed.");
    }
  }

  if (error) {
    return (
      <div className="app-frame">
        <div className="editor-shell">
          <header className="no-print doc-toolbar">
            <div className="doc-toolbar-row">
              <Toolbar
                editor={null}
                menuOpen={menuOpen}
                onMenuClick={() => setMenuOpen((value) => !value)}
              />
              <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
            </div>
          </header>
          <main className="px-6 py-16">
            <p className="text-red-600">{error}</p>
          </main>
        </div>
      </div>
    );
  }

  if (!resume) {
    return (
      <div className="app-frame">
        <div className="editor-shell">
          <header className="no-print doc-toolbar">
            <div className="doc-toolbar-row">
              <Toolbar
                editor={null}
                menuOpen={menuOpen}
                onMenuClick={() => setMenuOpen((value) => !value)}
              />
              <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
            </div>
          </header>
          <p className="px-6 py-16 text-sm">Loading…</p>
        </div>
      </div>
    );
  }

  const { width, height } = resume.document.page_size_pt;
  const margins = resume.document.margins_pt ?? {
    left: 28,
    right: 22,
    top: 18,
    bottom: 18,
  };

  return (
    <div className="app-frame">
      <div className="editor-shell">
        <header className="no-print doc-toolbar">
          <div className="doc-toolbar-row">
            <Toolbar
              editor={editor}
              menuOpen={menuOpen}
              onMenuClick={() => setMenuOpen((value) => !value)}
            />
            <div className="doc-toolbar-actions">
              <span className="doc-toolbar-status">{status}</span>
              <button
                type="button"
                onClick={onSave}
                className="doc-action doc-action-primary"
              >
                Save
              </button>
              <button type="button" onClick={onDownload} className="doc-action">
                Download PDF
              </button>
            </div>
            <Sidebar
              open={menuOpen}
              onClose={() => setMenuOpen(false)}
              fileName={resume.document.source_file}
              currentId={resume.id}
            />
          </div>
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

      <ChatPanel
        resumeId={resume.id}
        getBlocks={currentBlocks}
        getBlockText={blockText}
        onApplyEdit={applyEdit}
      />

      {noteOpen ? (
        <div className="note-modal-backdrop">
          <form className="note-modal" onSubmit={confirmDownload}>
            <h2 className="note-modal-title">Add a note</h2>
            <p className="note-modal-help">
              This note is the key you will use in the sidebar search to find
              this resume later.
            </p>
            <input
              className="note-modal-input"
              value={noteDraft}
              onChange={(event) => setNoteDraft(event.target.value)}
              placeholder="e.g. google-interview"
              autoFocus
            />
            <div className="note-modal-actions">
              <button
                type="button"
                className="doc-action"
                onClick={() => setNoteOpen(false)}
              >
                Cancel
              </button>
              <button type="submit" className="doc-action doc-action-primary">
                Download
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
