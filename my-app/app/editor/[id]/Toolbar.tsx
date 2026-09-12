"use client";

import type { ReactNode } from "react";
import type { Editor } from "@tiptap/react";

/**
 * Concept: a menubar, not a pile of labeled buttons.
 * Each control reads the current TipTap marks/attrs and writes a command.
 * The editor re-renders this on selectionUpdate, so dropdowns stay in sync.
 */

const FONTS = [
  { label: "Times New Roman", value: '"Times New Roman", Times, serif' },
  { label: "Arial", value: "Helvetica, Arial, sans-serif" },
  { label: "Courier", value: "Courier, monospace" },
] as const;

const SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 36];

function currentFont(editor: Editor): string {
  const family = String(editor.getAttributes("textStyle").fontFamily || "");
  const lower = family.toLowerCase();
  if (lower.includes("courier")) return "Courier, monospace";
  if (lower.includes("times")) return '"Times New Roman", Times, serif';
  if (lower.includes("helvetica") || lower.includes("arial")) {
    return "Helvetica, Arial, sans-serif";
  }
  return "";
}

function currentSize(editor: Editor): string {
  const size = String(editor.getAttributes("textStyle").fontSize || "");
  const value = parseFloat(size);
  return Number.isFinite(value) ? String(value) : "";
}

function currentColor(editor: Editor): string {
  const color = String(editor.getAttributes("textStyle").color || "#000000");
  return /^#[0-9a-fA-F]{6}$/.test(color) ? color : "#000000";
}

function ToolButton({
  label,
  active,
  disabled,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={`doc-tool ${active ? "is-active" : ""}`}
    >
      {children}
    </button>
  );
}

function DotsIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <circle cx="12" cy="5" r="1.8" fill="currentColor" />
      <circle cx="12" cy="12" r="1.8" fill="currentColor" />
      <circle cx="12" cy="19" r="1.8" fill="currentColor" />
    </svg>
  );
}

export default function Toolbar({
  editor,
  menuOpen,
  onMenuClick,
}: {
  editor: Editor | null;
  menuOpen: boolean;
  onMenuClick: () => void;
}) {
  const menuButton = (
    <div className="doc-toolbar-group">
      <ToolButton
        label={menuOpen ? "Close menu" : "Open menu"}
        active={menuOpen}
        onClick={onMenuClick}
      >
        <DotsIcon />
      </ToolButton>
    </div>
  );

  if (!editor) {
    return <div className="doc-toolbar-main">{menuButton}</div>;
  }

  const font = currentFont(editor);
  const size = currentSize(editor);
  const color = currentColor(editor);
  const sizeOptions =
    size && !SIZES.includes(Number(size))
      ? [Number(size), ...SIZES].sort((a, b) => a - b)
      : SIZES;

  return (
    <div className="doc-toolbar-main">
      {menuButton}
      <div className="doc-toolbar-group">
        <ToolButton
          label="Undo"
          disabled={!editor.can().undo()}
          onClick={() => editor.chain().focus().undo().run()}
        >
          <UndoIcon />
        </ToolButton>
        <ToolButton
          label="Redo"
          disabled={!editor.can().redo()}
          onClick={() => editor.chain().focus().redo().run()}
        >
          <RedoIcon />
        </ToolButton>
      </div>

      <div className="doc-toolbar-group">
        <select
          aria-label="Font"
          className="doc-select doc-select-font"
          value={font}
          onChange={(event) => {
            editor.chain().focus().setFontFamily(event.target.value).run();
          }}
        >
          <option value="" disabled>
            Font
          </option>
          {FONTS.map((item) => (
            <option
              key={item.value}
              value={item.value}
              style={{ fontFamily: item.value }}
            >
              {item.label}
            </option>
          ))}
        </select>
        <select
          aria-label="Font size"
          className="doc-select doc-select-size"
          value={size}
          onChange={(event) => {
            editor.chain().focus().setFontSize(`${event.target.value}pt`).run();
          }}
        >
          <option value="" disabled>
            Size
          </option>
          {sizeOptions.map((item) => (
            <option key={item} value={String(item)}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="doc-toolbar-group">
        <ToolButton
          label="Bold"
          active={editor.isActive("bold")}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          <span className="doc-tool-letter" style={{ fontWeight: 700 }}>
            B
          </span>
        </ToolButton>
        <ToolButton
          label="Italic"
          active={editor.isActive("italic")}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          <span className="doc-tool-letter" style={{ fontStyle: "italic" }}>
            I
          </span>
        </ToolButton>
        <ToolButton
          label="Underline"
          active={editor.isActive("underline")}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
        >
          <span
            className="doc-tool-letter"
            style={{ textDecoration: "underline" }}
          >
            U
          </span>
        </ToolButton>
        <label className="doc-color" title="Text color">
          <span
            className="doc-color-letter"
            style={{ borderBottomColor: color }}
          >
            A
          </span>
          <input
            type="color"
            aria-label="Text color"
            value={color}
            onChange={(event) => {
              editor.chain().focus().setColor(event.target.value).run();
            }}
          />
        </label>
      </div>

      <div className="doc-toolbar-group">
        <ToolButton
          label="Align left"
          active={
            editor.isActive({ textAlign: "left" }) ||
            !editor.getAttributes("paragraph").textAlign
          }
          onClick={() => editor.chain().focus().setTextAlign("left").run()}
        >
          <AlignIcon kind="left" />
        </ToolButton>
        <ToolButton
          label="Align center"
          active={editor.isActive({ textAlign: "center" })}
          onClick={() => editor.chain().focus().setTextAlign("center").run()}
        >
          <AlignIcon kind="center" />
        </ToolButton>
        <ToolButton
          label="Align right"
          active={editor.isActive({ textAlign: "right" })}
          onClick={() => editor.chain().focus().setTextAlign("right").run()}
        >
          <AlignIcon kind="right" />
        </ToolButton>
      </div>

      <div className="doc-toolbar-group">
        <ToolButton
          label="Clear formatting"
          onClick={() =>
            editor
              .chain()
              .focus()
              .unsetBold()
              .unsetItalic()
              .unsetUnderline()
              .unsetColor()
              .run()
          }
        >
          <ClearIcon />
        </ToolButton>
      </div>
    </div>
  );
}

function UndoIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12.5 8c-2.6 0-5 1-6.9 2.6L3 8v8h8l-2.6-2.6A6.8 6.8 0 0 1 12.5 11c2.8 0 5.2 1.7 6.3 4.1l2.1-.7C19.4 10.6 16.2 8 12.5 8z"
      />
    </svg>
  );
}

function RedoIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="currentColor"
        d="M11.5 8c2.6 0 5 1 6.9 2.6L21 8v8h-8l2.6-2.6A6.8 6.8 0 0 0 11.5 11c-2.8 0-5.2 1.7-6.3 4.1l-2.1-.7C4.6 10.6 7.8 8 11.5 8z"
      />
    </svg>
  );
}

function AlignIcon({ kind }: { kind: "left" | "center" | "right" }) {
  const lines =
    kind === "left" ? [2, 2, 2] : kind === "right" ? [8, 6, 8] : [5, 4, 5];
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <rect x={lines[0]} y="6" width="14" height="2" fill="currentColor" />
      <rect x={lines[1]} y="11" width="16" height="2" fill="currentColor" />
      <rect x={lines[2]} y="16" width="14" height="2" fill="currentColor" />
    </svg>
  );
}

/** A struck-through letter A: strip the styling off this text. */
function ClearIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    >
      <path d="M7 16.5 11.2 6.5l4.2 10" />
      <path d="M8.6 13.2h5.2" />
      <path d="M4.5 19.5 19.5 4.5" />
    </svg>
  );
}
