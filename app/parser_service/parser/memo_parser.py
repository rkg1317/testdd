"""Deterministic Word-memo parsing into provenance-tagged passages.

Each non-empty paragraph becomes one Passage with a stable 0-based index, so a
retrieved passage can always cite ``document · passage N``. PDF support (pdfplumber)
is a later-phase addition behind the same Passage interface.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from .schema import Passage, PassageRef


def parse_memo(path) -> list:
    """Parse a .docx memo into a list of provenance-tagged passages."""
    path = Path(path)
    fname = path.name
    doc = Document(str(path))

    passages: list = []
    index = 0
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name if para.style and para.style.name else "") or ""
        kind = "heading" if style.lower().startswith("heading") else "paragraph"
        passages.append(
            Passage(content=text, ref=PassageRef(document=fname, passage=index, kind=kind))
        )
        index += 1
    return passages
