"""
Extracts a PDF's exact text content + styling + layout into a JSON file
that is "round-trip safe": feeding this JSON back into json_to_pdf.py
(or any similar renderer) reproduces the same PDF pixel-for-pixel.

Concept: PyMuPDF's page.get_text("dict") already breaks the page into
blocks -> lines -> spans, and each span carries exactly what we need:
`text`, `font`, `size`, `color` (packed int), `origin` (baseline x/y in a
TOP-LEFT coordinate system - same convention the original resume JSON used),
and `bbox`. Vector graphics (like divider rules) come from a separate call,
page.get_drawings().

We don't trust the embedded font's *name* (PDFs can subset/rename fonts to
anything, e.g. "ABCDEF+Times-Bold"). Instead we decode the `flags` bitfield
PyMuPDF gives us, which tells us bold/italic/serif/monospace directly, and
snap to one of reportlab's 14 standard fonts. That keeps the JSON portable
and guarantees whatever renders it back doesn't need the original font file.
"""

import json
import sys
from pathlib import Path

import fitz  # PyMuPDF

# Bit flags PyMuPDF sets on each span (see PyMuPDF docs for TextPage flags).
FLAG_ITALIC = 1 << 1       # 2
FLAG_SERIF = 1 << 2        # 4
FLAG_MONOSPACED = 1 << 3   # 8
FLAG_BOLD = 1 << 4         # 16


def flags_to_standard_font(flags: int) -> str:
    """Map PyMuPDF's bold/italic/serif/monospace bits onto one of
    reportlab's 14 standard fonts, so the JSON never depends on the
    original PDF's (possibly subsetted/renamed) embedded font."""
    bold = bool(flags & FLAG_BOLD)
    italic = bool(flags & FLAG_ITALIC)

    if flags & FLAG_MONOSPACED:
        family = "Courier"
        variants = {
            (False, False): "Courier",
            (True, False): "Courier-Bold",
            (False, True): "Courier-Oblique",
            (True, True): "Courier-BoldOblique",
        }
    elif flags & FLAG_SERIF:
        variants = {
            (False, False): "Times-Roman",
            (True, False): "Times-Bold",
            (False, True): "Times-Italic",
            (True, True): "Times-BoldItalic",
        }
    else:
        variants = {
            (False, False): "Helvetica",
            (True, False): "Helvetica-Bold",
            (False, True): "Helvetica-Oblique",
            (True, True): "Helvetica-BoldOblique",
        }

    return variants[(bold, italic)]


def int_color_to_hex(color_int: int) -> str:
    """PyMuPDF text spans give color as one packed sRGB integer."""
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    return f"#{r:02X}{g:02X}{b:02X}"


def float_color_to_hex(rgb) -> str:
    """page.get_drawings() gives color as an (r, g, b) tuple of 0.0-1.0 floats."""
    r, g, b = (round(c * 255) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def extract_page(page, page_index: int) -> tuple[list[dict], list[dict]]:
    raw_elements = []
    text_dict = page.get_text("dict")

    for block in text_dict["blocks"]:
        if block.get("type") != 0:
            continue  # skip image blocks, we only care about text
        for line_idx, line in enumerate(block["lines"]):
            for span_idx, span in enumerate(line["spans"]):
                flags = span["flags"]
                raw_elements.append(
                    {
                        "page": page_index,
                        "block": block["number"],
                        "line": line_idx,
                        "span": span_idx,
                        "text": span["text"],
                        "font": flags_to_standard_font(flags),
                        "source_font": span["font"],  # original embedded font, kept for reference
                        "size_pt": round(span["size"], 2),
                        "color_hex": int_color_to_hex(span["color"]),
                        "bold": bool(flags & FLAG_BOLD),
                        "italic": bool(flags & FLAG_ITALIC),
                        "bbox": [round(v, 2) for v in span["bbox"]],
                        "origin": [round(v, 2) for v in span["origin"]],
                    }
                )

    divider_lines = []
    for drawing in page.get_drawings():
        color = drawing.get("color")
        width = drawing.get("width") or 0.75
        if not color:
            continue
        for item in drawing["items"]:
            kind = item[0]
            if kind != "l":  # only care about straight line segments (the divider rules)
                continue
            p0, p1 = item[1], item[2]
            divider_lines.append(
                {
                    "page": page_index,
                    "x0": round(p0.x, 2),
                    "y0": round(p0.y, 2),
                    "x1": round(p1.x, 2),
                    "y1": round(p1.y, 2),
                    "width_pt": round(width, 2),
                    "color_hex": float_color_to_hex(color),
                }
            )

    return raw_elements, divider_lines


def extract_from_bytes(pdf_bytes: bytes, source_name: str) -> dict:
    """Same extraction as the CLI, but from in-memory PDF bytes so FastAPI
    can call this without writing a temp file first."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise ValueError("This PDF has no pages.")

    all_raw_elements = []
    all_divider_lines = []
    first_page_rect = doc[0].rect

    for page_index, page in enumerate(doc):
        raw_elements, divider_lines = extract_page(page, page_index)
        all_raw_elements.extend(raw_elements)
        all_divider_lines.extend(divider_lines)

    return {
        "document": {
            "source_file": source_name,
            "page_count": doc.page_count,
            "page_size_pt": {
                "width": round(first_page_rect.width, 2),
                "height": round(first_page_rect.height, 2),
            },
            "units": "points (1/72 inch); origin top-left, y increases downward",
        },
        "layout": {
            "divider_lines": all_divider_lines,
        },
        "raw_elements": all_raw_elements,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 pdf_to_json.py <input.pdf> [output.json]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else pdf_path.with_suffix(".json")
    output = extract_from_bytes(pdf_path.read_bytes(), pdf_path.name)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}  ({len(output['raw_elements'])} text spans, {len(output['layout']['divider_lines'])} lines)")


if __name__ == "__main__":
    main()
