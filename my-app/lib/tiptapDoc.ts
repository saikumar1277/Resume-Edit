import type { JSONContent } from "@tiptap/core";
import type { Block, DividerBlock, ParagraphBlock, Run } from "./types";

export function cssFont(font: string): string {
  if (font.startsWith("Times")) return '"Times New Roman", Times, serif';
  if (font.startsWith("Courier")) return "Courier, monospace";
  return "Helvetica, Arial, sans-serif";
}

/** Turn CSS family + bold/italic back into one of ReportLab's 14 fonts. */
export function pdfFont(
  cssFamily: string | undefined,
  bold: boolean,
  italic: boolean,
): string {
  const family = (cssFamily || "").toLowerCase();
  if (family.includes("courier")) {
    if (bold && italic) return "Courier-BoldOblique";
    if (bold) return "Courier-Bold";
    if (italic) return "Courier-Oblique";
    return "Courier";
  }
  if (family.includes("times")) {
    if (bold && italic) return "Times-BoldItalic";
    if (bold) return "Times-Bold";
    if (italic) return "Times-Italic";
    return "Times-Roman";
  }
  if (bold && italic) return "Helvetica-BoldOblique";
  if (bold) return "Helvetica-Bold";
  if (italic) return "Helvetica-Oblique";
  return "Helvetica";
}

function parseSizePt(fontSize: string | undefined): number {
  if (!fontSize) return 10;
  const value = parseFloat(fontSize);
  return Number.isFinite(value) ? value : 10;
}

function runToTextNode(run: Run): JSONContent | null {
  if (run.text === "") return null;
  const marks: { type: string; attrs?: Record<string, string> }[] = [
    {
      type: "textStyle",
      attrs: {
        fontFamily: cssFont(run.font),
        fontSize: `${run.size_pt}pt`,
        color: run.color_hex,
      },
    },
  ];
  if (run.bold) marks.push({ type: "bold" });
  if (run.italic) marks.push({ type: "italic" });
  return { type: "text", text: run.text, marks };
}

export function blocksToTiptap(blocks: Block[]): JSONContent {
  const content: JSONContent[] = blocks.map((block) => {
    if (block.type === "divider") {
      return {
        type: "divider",
        attrs: {
          widthPt: block.width_pt,
          colorHex: block.color_hex,
          blockId: block.id,
        },
      };
    }

    const textNodes = block.runs
      .map(runToTextNode)
      .filter((node): node is JSONContent => node !== null);

    return {
      type: "paragraph",
      attrs: {
        blockId: block.id,
        blockType: block.type,
      },
      ...(textNodes.length > 0 ? { content: textNodes } : {}),
    };
  });

  return { type: "doc", content };
}

function marksOf(node: JSONContent): JSONContent[] {
  return node.marks ?? [];
}

function runFromTextNode(node: JSONContent): Run {
  const marks = marksOf(node);
  const style = marks.find((mark) => mark.type === "textStyle")?.attrs ?? {};
  const bold = marks.some((mark) => mark.type === "bold");
  const italic = marks.some((mark) => mark.type === "italic");
  return {
    text: node.text ?? "",
    font: pdfFont(style.fontFamily, bold, italic),
    size_pt: parseSizePt(style.fontSize),
    color_hex: style.color || "#000000",
    bold,
    italic,
  };
}

function paragraphFromNode(node: JSONContent, index: number): ParagraphBlock {
  const runs = (node.content ?? [])
    .filter((child) => child.type === "text")
    .map(runFromTextNode);

  return {
    id: node.attrs?.blockId || `b${index}`,
    type: node.attrs?.blockType === "split_row" ? "split_row" : "paragraph",
    runs:
      runs.length > 0
        ? runs
        : [
            {
              text: "",
              font: "Helvetica",
              size_pt: 10,
              color_hex: "#000000",
              bold: false,
              italic: false,
            },
          ],
  };
}

function dividerFromNode(node: JSONContent, index: number): DividerBlock {
  return {
    id: node.attrs?.blockId || `b${index}`,
    type: "divider",
    width_pt: node.attrs?.widthPt ?? 0.75,
    color_hex: node.attrs?.colorHex ?? "#000000",
  };
}

export function tiptapToBlocks(doc: JSONContent): Block[] {
  const nodes = doc.content ?? [];
  return nodes.map((node, index) => {
    if (node.type === "divider") {
      return dividerFromNode(node, index);
    }
    return paragraphFromNode(node, index);
  });
}
