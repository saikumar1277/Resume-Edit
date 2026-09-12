"""
The convert path, in order:

  pdf_to_json.py     PDF bytes -> text spans + divider lines
  raw_to_blocks.py   spans -> paragraphs (blocks)
  convert.py         runs those two on upload
  blocks_to_pdf.py   blocks -> a new PDF on download
"""

from .blocks_to_pdf import fit_to_one_page
from .convert import ConvertError, convert_pdf

__all__ = ["ConvertError", "convert_pdf", "fit_to_one_page"]
