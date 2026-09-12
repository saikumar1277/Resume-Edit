"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { chatWithResume } from "../../../lib/api";
import type { Block, ChatMessage, ResumeEdit } from "../../../lib/types";

/**
 * Concept: suggest, then let the user decide.
 * The assistant answers with a message plus edits aimed at specific block
 * ids. Nothing touches the document until Accept is clicked, so a bad
 * suggestion costs one click to discard.
 */

/** Preview ** the same way boldMarkedTextNodes will apply it, so the card
 *  shows bold text instead of the markers themselves. */
function BoldMarked({ text }: { text: string }) {
  return (
    <>
      {text
        .split("**")
        .map((segment, index) =>
          index % 2 === 1 ? <strong key={index}>{segment}</strong> : segment,
        )}
    </>
  );
}

const STARTERS = [
  "Tighten my experience bullets",
  "What skills am I missing for a backend role?",
  "Suggest a project to add",
];

export default function ChatPanel({
  resumeId,
  getBlocks,
  getBlockText,
  onApplyEdit,
}: {
  resumeId: string;
  getBlocks: () => Block[];
  getBlockText: (blockId: string) => string;
  onApplyEdit: (edit: ResumeEdit) => boolean;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState<{ key: number; edit: ResumeEdit }[]>(
    [],
  );
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const nextKey = useRef(0);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [messages, pending, busy]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;

    const history: ChatMessage[] = [
      ...messages,
      { role: "user", content: question },
    ];
    setMessages(history);
    setDraft("");
    setError("");
    setBusy(true);
    try {
      const reply = await chatWithResume(resumeId, getBlocks(), history);
      setMessages([...history, { role: "assistant", content: reply.reply }]);
      setPending((items) => [
        ...items,
        ...reply.edits.map((edit) => ({ key: nextKey.current++, edit })),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The assistant failed.");
    } finally {
      setBusy(false);
    }
  }

  function accept(key: number, edit: ResumeEdit) {
    if (!onApplyEdit(edit)) {
      setError("That line has changed too much to patch. Ask again.");
    }
    setPending((items) => items.filter((item) => item.key !== key));
  }

  return (
    <aside className="chat-panel no-print">
      <div className="chat-head">
        <p className="chat-title">Resume assistant</p>
        <p className="chat-sub">Suggestions apply only when you accept them.</p>
      </div>

      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && pending.length === 0 ? (
          <div className="chat-starters">
            {STARTERS.map((starter) => (
              <button
                key={starter}
                type="button"
                className="chat-starter"
                onClick={() => send(starter)}
              >
                {starter}
              </button>
            ))}
          </div>
        ) : null}

        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`chat-bubble chat-bubble-${message.role}`}
          >
            {message.content}
          </div>
        ))}

        {pending.map(({ key, edit }) => (
          <div key={key} className="chat-edit">
            <p className="chat-edit-label">
              {edit.op === "insert_after" ? "Add a new line" : "Rewrite"}
            </p>
            {edit.op === "replace" ? (
              <p className="chat-edit-before">{getBlockText(edit.block_id)}</p>
            ) : null}
            <p className="chat-edit-after">
              <BoldMarked text={edit.text} />
            </p>
            <div className="chat-edit-actions">
              <button
                type="button"
                className="doc-action"
                onClick={() =>
                  setPending((items) =>
                    items.filter((item) => item.key !== key),
                  )
                }
              >
                Reject
              </button>
              <button
                type="button"
                className="doc-action doc-action-primary"
                onClick={() => accept(key, edit)}
              >
                Accept
              </button>
            </div>
          </div>
        ))}

        {busy ? <p className="chat-status">Thinking…</p> : null}
        {error ? <p className="chat-error">{error}</p> : null}
      </div>

      <form
        className="chat-composer"
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          send(draft);
        }}
      >
        <textarea
          className="chat-input"
          value={draft}
          rows={2}
          placeholder="Ask for a rewrite, a missing skill, a project…"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              send(draft);
            }
          }}
        />
        <button
          type="submit"
          className="doc-action doc-action-primary"
          disabled={busy || !draft.trim()}
        >
          Send
        </button>
      </form>
    </aside>
  );
}
