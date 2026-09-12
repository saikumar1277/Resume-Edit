"""
Upload step: PDF bytes -> { document, blocks }.

Uses pdf_to_json (spans) then raw_to_blocks (paragraphs), then drops
underlines into the block list. Only blocks are stored.
"""

from .pdf_to_json import extract_from_bytes
from .raw_to_blocks import group_into_blocks

DEFAULT_MARGINS = {"left": 28.0, "right": 22.0, "top": 18.0, "bottom": 18.0}
MIN_MARGIN_PT = 8.0
# If text never reaches an edge, "margin" is just leftover page. Cap that.
MAX_REASONABLE_MARGIN_PT = 72.0
DIVIDER_ROW_TOLERANCE_PT = 2.0


class ConvertError(ValueError):
    pass


def measure_margins(raw_elements: list[dict], page_size: dict) -> dict:
    """Copy the original page's whitespace from span boxes, not guesses."""
    boxes = [el["bbox"] for el in raw_elements if el.get("bbox")]
    if not boxes:
        return dict(DEFAULT_MARGINS)

    width = page_size["width"]
    height = page_size["height"]
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = width - max(box[2] for box in boxes)
    bottom = height - max(box[3] for box in boxes)
    return {
        "left": max(MIN_MARGIN_PT, round(left, 2)),
        "top": max(MIN_MARGIN_PT, round(top, 2)),
        "right": _edge_margin(right, DEFAULT_MARGINS["right"]),
        "bottom": _edge_margin(bottom, DEFAULT_MARGINS["bottom"]),
    }


def _edge_margin(value: float, fallback: float) -> float:
    value = max(MIN_MARGIN_PT, round(value, 2))
    if value > MAX_REASONABLE_MARGIN_PT:
        return fallback
    return value


def _horizontal_dividers(divider_lines: list[dict]) -> list[dict]:
    """Keep one rule per visual row. Skip vertical ticks and duplicate segments."""
    horizontal = []
    for line in divider_lines:
        dx = abs(line.get("x1", 0) - line.get("x0", 0))
        dy = abs(line.get("y1", 0) - line.get("y0", 0))
        if dx < dy:
            continue
        y = min(line.get("y0", 0), line.get("y1", 0))
        horizontal.append({**line, "_y": y})

    horizontal.sort(key=lambda line: line["_y"])
    merged = []
    for line in horizontal:
        if merged and abs(merged[-1]["_y"] - line["_y"]) < DIVIDER_ROW_TOLERANCE_PT:
            continue
        merged.append(line)
    return merged


def insert_divider_blocks(blocks: list[dict], divider_lines: list[dict]) -> list[dict]:
    """Put each underline into the flow under the text it sat below."""
    items: list[tuple[float, int, dict]] = []
    for block in blocks:
        items.append((float(block.get("y", 0)), 0, block))
    for line in _horizontal_dividers(divider_lines):
        divider = {
            "type": "divider",
            "width_pt": line.get("width_pt", 0.75),
            "color_hex": line.get("color_hex", "#000000"),
        }
        items.append((float(line["_y"]), 1, divider))

    items.sort(key=lambda item: (item[0], item[1]))
    result = []
    for _, _, payload in items:
        next_block = {k: v for k, v in payload.items() if k != "y"}
        next_block["id"] = f"b{len(result)}"
        result.append(next_block)
    return result


def convert_pdf(pdf_bytes: bytes, filename: str) -> dict:
    extracted = extract_from_bytes(pdf_bytes, filename)

    if extracted["document"]["page_count"] < 1:
        raise ConvertError("This PDF has no pages.")

    if not extracted["raw_elements"]:
        raise ConvertError("Could not find any text in this PDF.")

    margins = measure_margins(
        extracted["raw_elements"],
        extracted["document"]["page_size_pt"],
    )
    blocks = group_into_blocks(extracted["raw_elements"])
    if not blocks:
        raise ConvertError("Could not turn this PDF into editable paragraphs.")

    blocks = insert_divider_blocks(
        blocks,
        extracted.get("layout", {}).get("divider_lines", []),
    )

    return {
        "document": {
            **extracted["document"],
            "margins_pt": margins,
        },
        "blocks": blocks,
    }
