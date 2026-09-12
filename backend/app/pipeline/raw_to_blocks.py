"""
Converts pdf_to_json.py's `raw_elements` (a flat list of every individual
text span, positioned by x/y coordinate) into a flowing "blocks/runs"
document: one block per logical line/paragraph, each block holding one or
more styled "runs".

Concept: this is the same "paragraph containing styled runs" shape used by
real rich-text editors (Google Docs, Word, TipTap/Lexical) - each block is
one line or wrapped paragraph, each run is a contiguous piece of text
sharing one font/size/color/bold/italic.

THE HARD PART: deciding when two consecutive physical PDF lines are really
one wrapped paragraph/bullet (should become one block) vs. two separate,
independent lines that just happen to sit close together (should stay two
blocks). We use three geometric signals together, calibrated against real
resume data - see notes inline. No single signal is reliable alone:
  - vertical gap alone fails on short label lines stacked closely
    (e.g. "Languages: ..." / "Frontend: ..." look just as "tight" as a
    real wrapped line).
  - a line reaching close to the right margin can also happen because of
    right-aligned content (e.g. a date on the same line as a job title),
    not just because it wrapped - so we still require matching style.

NOT handled yet: multi-column layouts (see pdf_to_json.py docstring) - this
assumes single top-to-bottom reading order.
"""

import json
import re
import sys
from pathlib import Path

# Same signal blocks_to_pdf uses for title + date on one row.
BIG_GAP_RE = re.compile(r" {15,}")

BULLET_CHARS = ("•", "-", "‣", "▪", "◦", "*", "·")

# Tuned against real extracted resume data (see chat/testing):
SAME_ROW_GAP_PT = 1.5       # gap this small = same physical row, different span group
MAX_CONTINUATION_RATIO = 1.4  # gap / prev_font_size above this = a new item, not a wrap
MAX_SIZE_DIFF_PT = 0.5       # font size must match closely to be "the same text style"
RIGHT_MARGIN_TOLERANCE_PT = 60  # how close to the page's max right-edge counts as "wrapped"


def is_bullet_start(text: str) -> bool:
    stripped = text.lstrip()
    return any(stripped.startswith(ch + " ") or stripped == ch for ch in BULLET_CHARS)


def build_physical_lines(raw_elements: list[dict]) -> list[dict]:
    """Group spans into physical PDF lines, keeping the geometry we need
    to later decide which lines should merge into one flowing block."""
    ordered = sorted(
        (el for el in raw_elements if el["text"].strip() != ""),
        key=lambda el: (el["page"], el["block"], el["line"], el["span"]),
    )

    lines: list[dict] = []
    current_key = None
    current_spans: list[dict] = []

    def flush():
        if not current_spans:
            return
        first = current_spans[0]
        last = current_spans[-1]
        lines.append(
            {
                "page": current_key[0],
                "spans": current_spans.copy(),
                "text": "".join(s["text"] for s in current_spans),
                "y": first["origin"][1],
                # Style at the START of the line (used when this line is the
                # *current* one being joined onto something before it).
                "font": first["font"],
                "bold": first["bold"],
                "size_pt": first["size_pt"],
                # Style at the END of the line (used when this line is the
                # *previous* one - i.e. the style right at the wrap point,
                # which can differ from the line's opening style, e.g. a
                # bold "hook" phrase followed by regular text).
                "end_font": last["font"],
                "end_bold": last["bold"],
                "end_size_pt": last["size_pt"],
                "right_edge": max(s["bbox"][2] for s in current_spans),
            }
        )

    for el in ordered:
        key = (el["page"], el["block"], el["line"])
        if key != current_key:
            flush()
            current_spans = []
            current_key = key
        current_spans.append(el)
    flush()

    return lines


def decide_join(prev: dict, curr: dict, right_margin: float) -> str:
    """Returns "same_row", "continuation", or "new_block"."""
    if prev["page"] != curr["page"]:
        return "new_block"

    gap = curr["y"] - prev["y"]

    if abs(gap) < SAME_ROW_GAP_PT:
        # Same physical row, just split into separate span groups by
        # PyMuPDF (e.g. a bullet glyph vs. the text following it).
        return "same_row"

    if gap <= 0:
        return "new_block"  # out-of-order y, don't guess

    if is_bullet_start(curr["text"]):
        return "new_block"  # a new bullet always starts a new block

    # Compare the style at the END of the previous line (the wrap point)
    # against the style at the START of the current line - not the
    # previous line's opening style, which can differ (e.g. a bold hook
    # phrase followed by regular text later on the same line).
    style_matches = (
        prev["end_font"] == curr["font"]
        and prev["end_bold"] == curr["bold"]
        and abs(prev["end_size_pt"] - curr["size_pt"]) <= MAX_SIZE_DIFF_PT
    )
    ratio = gap / prev["end_size_pt"]
    ran_out_of_room = prev["right_edge"] >= right_margin - RIGHT_MARGIN_TOLERANCE_PT

    if style_matches and ratio <= MAX_CONTINUATION_RATIO and ran_out_of_room:
        return "continuation"

    return "new_block"


def group_into_blocks(raw_elements: list[dict]) -> list[dict]:
    lines = build_physical_lines(raw_elements)
    if not lines:
        return []

    right_margin = max(l["right_edge"] for l in lines)

    blocks: list[dict] = []
    current_runs: list[dict] = []
    current_page = lines[0]["page"]
    current_y = lines[0]["y"]
    prev_line = None

    def flush():
        if current_runs:
            text = "".join(r["text"] for r in current_runs)
            block_type = "split_row" if BIG_GAP_RE.search(text) else "paragraph"
            blocks.append(
                {
                    "id": f"b{len(blocks)}",
                    "type": block_type,
                    "page": current_page,
                    "y": current_y,
                    "runs": current_runs.copy(),
                }
            )

    def runs_from(line: dict) -> list[dict]:
        return [
            {
                "text": s["text"],
                "font": s["font"],
                "size_pt": s["size_pt"],
                "color_hex": s["color_hex"],
                "bold": s["bold"],
                "italic": s["italic"],
            }
            for s in line["spans"]
        ]

    for line in lines:
        join = decide_join(prev_line, line, right_margin) if prev_line else "new_block"

        if join in ("same_row", "continuation") and current_runs:
            last_text = current_runs[-1]["text"]
            trimmed = last_text.rstrip()
            is_hyphenated_break = (
                join == "continuation"
                and trimmed.endswith("-")
                and not trimmed.endswith(" -")  # a real " - " dash, not a broken word
            )
            if not is_hyphenated_break and not last_text.endswith(" "):
                current_runs[-1] = {**current_runs[-1], "text": last_text + " "}
            current_runs.extend(runs_from(line))
        else:
            flush()
            current_runs = runs_from(line)
            current_page = line["page"]
            current_y = line["y"]

        prev_line = line

    flush()
    return blocks


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 raw_to_blocks.py <extracted.json> [output.json]")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else in_path.with_name(in_path.stem + "_blocks.json")
    )

    data = json.loads(in_path.read_text())
    blocks = group_into_blocks(data["raw_elements"])

    output = {"document": data["document"], "blocks": blocks}

    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}  ({len(blocks)} blocks from {len(data['raw_elements'])} spans)")


if __name__ == "__main__":
    main()
