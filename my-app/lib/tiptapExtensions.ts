import { Node, mergeAttributes } from "@tiptap/core";
import Paragraph from "@tiptap/extension-paragraph";

/**
 * A section underline. Atom = one piece; the user cannot type inside it.
 * We store the original thickness/color so download can draw the same rule.
 */
export const ResumeDivider = Node.create({
  name: "divider",
  group: "block",
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      widthPt: { default: 0.75 },
      colorHex: { default: "#000000" },
      blockId: { default: null },
    };
  },

  parseHTML() {
    return [{ tag: "hr[data-resume-divider]" }];
  },

  renderHTML({ HTMLAttributes }) {
    const color = HTMLAttributes.colorHex || "#000000";
    const thickness = HTMLAttributes.widthPt || 0.75;
    return [
      "hr",
      mergeAttributes(HTMLAttributes, {
        "data-resume-divider": "",
        style: `background:${color};height:${thickness}pt;border:none;margin:4pt 0;`,
      }),
    ];
  },
});

/** Keep our block id/type on each paragraph so save can rebuild the same list. */
export const ResumeParagraph = Paragraph.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      blockId: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-block-id"),
        renderHTML: (attributes) =>
          attributes.blockId ? { "data-block-id": attributes.blockId } : {},
      },
      blockType: {
        default: "paragraph",
        parseHTML: (element) =>
          element.getAttribute("data-block-type") || "paragraph",
        renderHTML: (attributes) => ({
          "data-block-type": attributes.blockType || "paragraph",
        }),
      },
    };
  },
});
