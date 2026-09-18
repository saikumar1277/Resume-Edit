"use client";

import type { ReactNode } from "react";
import type { Editor } from "@tiptap/react";
import {
  AlignCenterIcon,
  AlignLeftIcon,
  AlignRightIcon,
  BoldIcon,
  ItalicIcon,
  Redo2Icon,
  RemoveFormattingIcon,
  UnderlineIcon,
  Undo2Icon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Toggle, toggleVariants } from "@/components/ui/toggle";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

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

function ToolToggle({
  label,
  pressed,
  disabled,
  onPressedChange,
  children,
}: {
  label: string;
  pressed?: boolean;
  disabled?: boolean;
  onPressedChange: () => void;
  children: ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Toggle
            size="sm"
            pressed={pressed}
            disabled={disabled}
            onPressedChange={onPressedChange}
            aria-label={label}
          />
        }
      >
        {children}
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export default function Toolbar({ editor }: { editor: Editor | null }) {
  if (!editor) return null;

  const font = currentFont(editor);
  const size = currentSize(editor);
  const color = currentColor(editor);
  const sizeOptions =
    size && !SIZES.includes(Number(size))
      ? [Number(size), ...SIZES].sort((a, b) => a - b)
      : SIZES;

  return (
    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
      <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
        <ToolToggle
          label="Undo"
          disabled={!editor.can().undo()}
          onPressedChange={() => editor.chain().focus().undo().run()}
        >
          <Undo2Icon />
        </ToolToggle>
        <ToolToggle
          label="Redo"
          disabled={!editor.can().redo()}
          onPressedChange={() => editor.chain().focus().redo().run()}
        >
          <Redo2Icon />
        </ToolToggle>
      </div>

      <Separator orientation="vertical" className="mx-1 h-6" />

      <Select
        value={font || null}
        onValueChange={(value) => {
          if (value) editor.chain().focus().setFontFamily(value).run();
        }}
      >
        <SelectTrigger size="sm" className="w-38" aria-label="Font">
          <SelectValue placeholder="Font" />
        </SelectTrigger>
        <SelectContent alignItemWithTrigger={false}>
          {FONTS.map((item) => (
            <SelectItem key={item.value} value={item.value}>
              {item.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={size || null}
        onValueChange={(value) => {
          if (value) editor.chain().focus().setFontSize(`${value}pt`).run();
        }}
      >
        <SelectTrigger size="sm" className="w-16" aria-label="Font size">
          <SelectValue placeholder="Size" />
        </SelectTrigger>
        <SelectContent alignItemWithTrigger={false}>
          {sizeOptions.map((item) => (
            <SelectItem key={item} value={String(item)}>
              {item}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
        <ToolToggle
          label="Bold"
          pressed={editor.isActive("bold")}
          onPressedChange={() => editor.chain().focus().toggleBold().run()}
        >
          <BoldIcon />
        </ToolToggle>
        <ToolToggle
          label="Italic"
          pressed={editor.isActive("italic")}
          onPressedChange={() => editor.chain().focus().toggleItalic().run()}
        >
          <ItalicIcon />
        </ToolToggle>
        <ToolToggle
          label="Underline"
          pressed={editor.isActive("underline")}
          onPressedChange={() => editor.chain().focus().toggleUnderline().run()}
        >
          <UnderlineIcon />
        </ToolToggle>
        <Tooltip>
          <TooltipTrigger
            render={
              <label
                className={cn(
                  toggleVariants({ size: "sm" }),
                  "relative cursor-pointer",
                )}
              />
            }
          >
            <span
              className="text-sm font-bold leading-none"
              style={{ borderBottom: `2px solid ${color}` }}
            >
              A
            </span>
            <input
              type="color"
              aria-label="Text color"
              className="absolute inset-0 cursor-pointer opacity-0"
              value={color}
              onChange={(event) => {
                editor.chain().focus().setColor(event.target.value).run();
              }}
            />
          </TooltipTrigger>
          <TooltipContent>Text color</TooltipContent>
        </Tooltip>
      </div>

      <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
        <ToolToggle
          label="Align left"
          pressed={
            editor.isActive({ textAlign: "left" }) ||
            !editor.getAttributes("paragraph").textAlign
          }
          onPressedChange={() =>
            editor.chain().focus().setTextAlign("left").run()
          }
        >
          <AlignLeftIcon />
        </ToolToggle>
        <ToolToggle
          label="Align center"
          pressed={editor.isActive({ textAlign: "center" })}
          onPressedChange={() =>
            editor.chain().focus().setTextAlign("center").run()
          }
        >
          <AlignCenterIcon />
        </ToolToggle>
        <ToolToggle
          label="Align right"
          pressed={editor.isActive({ textAlign: "right" })}
          onPressedChange={() =>
            editor.chain().focus().setTextAlign("right").run()
          }
        >
          <AlignRightIcon />
        </ToolToggle>
      </div>

      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Clear formatting"
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
            />
          }
        >
          <RemoveFormattingIcon />
        </TooltipTrigger>
        <TooltipContent>Clear formatting</TooltipContent>
      </Tooltip>
    </div>
  );
}
