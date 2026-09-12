"""
Renders blocks/runs JSON (produced by raw_to_blocks.py) back into a PDF
using a real layout engine, instead of the fixed-x/y placement approach in
json_to_pdf.py. This is the piece that lets edited text reflow naturally:
if a block's text gets longer/shorter, ReportLab's Platypus flowables
recompute line-wrapping and push everything below it down (or up)
automatically, and will overflow onto a new page if content grows past
one page.

Concept: each `block` becomes one reportlab Paragraph. A paragraph can mix
several styles by wrapping each `run` in a <font face="..." size="..."
color="...">...</font> tag - ReportLab's small HTML-like markup language
for exactly this purpose. Since our `font` field is already one of
ReportLab's 14 standard font names (e.g. "Times-Bold"), it already encodes
bold/italic, so no separate <b>/<i> tags are needed.

AUTO-FIT: rather than hand-tuned spacing constants (which only work for
one specific resume's amount of content), we define a "comfortable"
spacing target and a "tightest legible" one, then binary-search between
them for the loosest spacing that still fits on one page. Only if spacing
alone can't do it do we fall back to a small, bounded font-size shrink -
mirroring how a person manually fitting a resume to one page would do it:
tighten spacing first, shrink text only as a last resort.
"""

import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import fitz  # PyMuPDF - used here to check the resulting page count
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .raw_to_blocks import is_bullet_start

# Measured directly from the original resume's actual text positions
# (min/max bbox across all spans) rather than guessed - resumes tend to
# use much tighter margins than typical documents to fit more on one page.
LEFT_MARGIN_PT = 28
RIGHT_MARGIN_PT = 22
TOP_MARGIN_PT = 18
BOTTOM_MARGIN_PT = 18

# A run of 15+ literal spaces is an unambiguous, purely mechanical signal
# (no guessing about meaning needed) that the original PDF right-aligned
# something on that line - e.g. a date - via absolute x positioning rather
# than actual typed spaces.
BIG_GAP_RE = re.compile(r" {15,}")

# "Comfortable" spacing targets (spacing_scale = 1.0) - generous, readable.
# At spacing_scale = 0.0 these collapse to single-line-height with no
# extra gap at all - the tightest a resume can look while still being
# legible. classify_role's job is only to decide *which* of these targets
# applies to a given block; the actual point values stay here.
BASE_LEADING_FACTOR = 1.20
BASE_ROLE_SPACE_BEFORE_FACTOR = {
    "header": 0.8,
    "entry_title": 0.35,
    "sub_line": 0.05,
    "bullet": 0.2,
    "body": 0.15,
}

MIN_FONT_SCALE = 0.85  # never shrink text below 85% of its extracted size
BINARY_SEARCH_STEPS = 8  # 2^-8 precision on the scale factor - plenty for points-based layout


def page_margins(data: dict) -> dict:
    stored = data.get("document", {}).get("margins_pt") or {}
    return {
        "left": stored.get("left", LEFT_MARGIN_PT),
        "right": stored.get("right", RIGHT_MARGIN_PT),
        "top": stored.get("top", TOP_MARGIN_PT),
        "bottom": stored.get("bottom", BOTTOM_MARGIN_PT),
    }


def is_divider(block: dict) -> bool:
    return block.get("type") == "divider"


def classify_role(block: dict, body_size: float) -> str:
    """Structural classification, always based on the *original* extracted
    sizes/styles - never on the scaled-for-display size, so shrinking for
    auto-fit can't accidentally change what counts as a header vs. body."""
    runs = block.get("runs") or []
    if not runs:
        return "body"
    size = runs[0]["size_pt"]
    bold = runs[0]["bold"]
    italic = runs[0]["italic"]
    text = "".join(r["text"] for r in runs)

    if bold and size > body_size + 0.5:
        return "header"
    if is_bullet_start(text):
        return "bullet"
    if italic and not bold:
        return "sub_line"
    if bold:
        return "entry_title"
    return "body"


ALIGN = {
    "left": TA_LEFT,
    "center": TA_CENTER,
    "right": TA_RIGHT,
}


def run_to_markup(run: dict, font_scale: float) -> str:
    text = escape(run["text"])
    size = run["size_pt"] * font_scale
    if run.get("underline"):
        text = f"<u>{text}</u>"
    return f'<font face="{run["font"]}" size="{size:.2f}" color="{run["color_hex"]}">{text}</font>'


def runs_to_paragraph(runs: list[dict], align, font_scale: float, leading_factor: float) -> Paragraph:
    markup = "".join(run_to_markup(r, font_scale) for r in runs) or " "
    size = (runs[0]["size_pt"] if runs else 10.0) * font_scale
    style = ParagraphStyle(
        name=f"style-{id(runs)}",
        fontName=runs[0]["font"] if runs else "Helvetica",
        fontSize=size,
        leading=size * leading_factor,
        alignment=align,
    )
    return Paragraph(markup, style)


def split_left_right(block: dict):
    """If a block contains a long literal-space gap, split it into
    (left_runs, right_runs) so it can be rendered as a 2-column table
    instead of a plain paragraph - Paragraph markup collapses whitespace
    (like HTML does), so relying on literal spaces to right-align text
    silently fails otherwise. Returns None if no such gap is found."""
    runs = block.get("runs") or []
    for i, run in enumerate(runs):
        match = BIG_GAP_RE.search(run["text"])
        if not match:
            continue
        left_text = run["text"][: match.start()]
        right_text = run["text"][match.end() :]
        left_runs = runs[:i] + ([{**run, "text": left_text}] if left_text else [])
        right_runs = ([{**run, "text": right_text}] if right_text else []) + runs[i + 1 :]
        if left_runs and right_runs:
            return left_runs, right_runs
    return None


def divider_flowable(block: dict, available_width: float):
    return HRFlowable(
        width=available_width,
        thickness=block.get("width_pt", 0.75),
        color=HexColor(block.get("color_hex", "#000000")),
        spaceBefore=1,
        spaceAfter=2,
    )


def block_to_flowable(block: dict, available_width: float, font_scale: float, leading_factor: float):
    if is_divider(block):
        return divider_flowable(block, available_width)

    split = split_left_right(block)
    if split is None:
        align = ALIGN.get(block.get("align") or "left", TA_LEFT)
        return runs_to_paragraph(block.get("runs") or [], align, font_scale, leading_factor)

    left_runs, right_runs = split
    left_para = runs_to_paragraph(left_runs, TA_LEFT, font_scale, leading_factor)
    right_para = runs_to_paragraph(right_runs, TA_RIGHT, font_scale, leading_factor)
    table = Table([[left_para, right_para]], colWidths=[available_width * 0.7, available_width * 0.3])
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def build_pdf(data: dict, spacing_scale: float, font_scale: float) -> tuple[bytes, int]:
    """Builds the resume PDF in memory at the given scale factors and
    returns (pdf_bytes, page_count). spacing_scale/font_scale = 1.0 means
    full "comfortable" spacing / original extracted font size."""
    page_w = data["document"]["page_size_pt"]["width"]
    page_h = data["document"]["page_size_pt"]["height"]
    margins = page_margins(data)
    available_width = page_w - margins["left"] - margins["right"]

    blocks = data["blocks"]
    sizes = [b["runs"][0]["size_pt"] for b in blocks if b.get("runs")]
    body_size = Counter(sizes).most_common(1)[0][0] if sizes else 10.0
    leading_factor = 1.0 + (BASE_LEADING_FACTOR - 1.0) * spacing_scale

    story = []
    for i, block in enumerate(blocks):
        if is_divider(block):
            story.append(divider_flowable(block, available_width))
            continue
        role = classify_role(block, body_size)
        scaled_size = (block["runs"][0]["size_pt"] if block.get("runs") else 10.0) * font_scale
        space_before = 0 if i == 0 else scaled_size * BASE_ROLE_SPACE_BEFORE_FACTOR[role] * spacing_scale
        if space_before:
            story.append(Spacer(1, space_before))
        story.append(block_to_flowable(block, available_width, font_scale, leading_factor))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_w, page_h),
        leftMargin=margins["left"],
        rightMargin=margins["right"],
        topMargin=margins["top"],
        bottomMargin=margins["bottom"],
    )
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    page_count = fitz.open(stream=pdf_bytes, filetype="pdf").page_count
    return pdf_bytes, page_count


def fit_to_one_page(data: dict) -> bytes:
    # Phase 1: comfortable spacing, full font size - maybe it already fits.
    pdf_bytes, pages = build_pdf(data, spacing_scale=1.0, font_scale=1.0)
    if pages <= 1:
        print("Fits comfortably at full spacing - no shrinking needed.")
        return pdf_bytes

    # Phase 2: binary search for the loosest spacing that still fits on
    # one page, keeping font size untouched.
    lo, hi = 0.0, 1.0
    best_bytes = None
    for _ in range(BINARY_SEARCH_STEPS):
        mid = (lo + hi) / 2
        pdf_bytes, pages = build_pdf(data, spacing_scale=mid, font_scale=1.0)
        if pages <= 1:
            best_bytes, lo = pdf_bytes, mid  # fits - try loosening further
        else:
            hi = mid  # too loose - tighten more
    if best_bytes is not None:
        print(f"Fit on one page by tightening spacing to {lo:.2f}x (1.0 = comfortable, 0.0 = tightest legible).")
        return best_bytes

    # Phase 3: spacing alone wasn't enough even at its tightest - fall
    # back to also shrinking font size, again via binary search, bounded
    # so text never becomes unreasonably small.
    lo, hi = MIN_FONT_SCALE, 1.0
    best_bytes = None
    for _ in range(BINARY_SEARCH_STEPS):
        mid = (lo + hi) / 2
        pdf_bytes, pages = build_pdf(data, spacing_scale=0.0, font_scale=mid)
        if pages <= 1:
            best_bytes, lo = pdf_bytes, mid
        else:
            hi = mid
    if best_bytes is not None:
        print(f"Spacing alone wasn't enough - also shrank font size to {lo:.0%} to fit one page.")
        return best_bytes

    print(f"Could not fit on one page even at tightest spacing and {MIN_FONT_SCALE:.0%} font size - allowing overflow.")
    pdf_bytes, _ = build_pdf(data, spacing_scale=0.0, font_scale=MIN_FONT_SCALE)
    return pdf_bytes


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 blocks_to_pdf.py <blocks.json> [output.pdf]")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else in_path.with_suffix(".pdf")

    data = json.loads(in_path.read_text())
    pdf_bytes = fit_to_one_page(data)
    out_path.write_bytes(pdf_bytes)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
