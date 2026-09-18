"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import TextAlign from "@tiptap/extension-text-align";
import { FontSize, TextStyle } from "@tiptap/extension-text-style";
import Underline from "@tiptap/extension-underline";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
      toast.success("Resume saved");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Save failed.";
      setStatus(message);
      toast.error(message);
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
      toast.success("PDF downloaded");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Download failed.";
      setStatus(message);
      toast.error(message);
    }
  }

  if (error) {
    return (
      <AppShell active="resumes">
        <main className="px-6 py-16">
          <p className="text-destructive">{error}</p>
        </main>
      </AppShell>
    );
  }

  if (!resume) {
    return (
      <AppShell active="resumes">
        <p className="px-6 py-16 text-sm text-muted-foreground">Loading…</p>
      </AppShell>
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
    <AppShell
      active="resumes"
      status={status}
      fileName={resume.document.source_file}
      currentId={resume.id}
      tools={<Toolbar editor={editor} />}
      actions={
        <>
          <Button type="button" onClick={onSave}>
            Save
          </Button>
          <Button type="button" variant="outline" onClick={onDownload}>
            Download PDF
          </Button>
        </>
      }
      aside={
        <ChatPanel
          resumeId={resume.id}
          getBlocks={currentBlocks}
          getBlockText={blockText}
          onApplyEdit={applyEdit}
        />
      }
    >
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

      <Dialog open={noteOpen} onOpenChange={setNoteOpen}>
        <DialogContent>
          <form onSubmit={confirmDownload} className="grid gap-4">
            <DialogHeader>
              <DialogTitle>Add a note</DialogTitle>
              <DialogDescription>
                This note is the key you will use in the menu search to find
                this resume later.
              </DialogDescription>
            </DialogHeader>
            <Input
              value={noteDraft}
              onChange={(event) => setNoteDraft(event.target.value)}
              placeholder="e.g. google-interview"
              autoFocus
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setNoteOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit">Download</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
