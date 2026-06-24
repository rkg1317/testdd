"""The citation schema — the trust spine of the platform.

Every value pulled from a source carries enough provenance to cite it back to its
origin, so no figure ever reaches the model or the user without a source:

  - tabular value  ->  CellRef{file, sheet, cell, row, column, header}
  - text passage   ->  PassageRef{document, passage, kind}

Research flagged this as a day-one decision: retrofitting provenance after the
first parser is written is a rewrite. Field names follow the agreed inter-node
data contract ({value, file, sheet, cell} ; {content, document, passage}).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Tabular provenance
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CellRef:
    """Where a single tabular value came from (A1-style, like Excel shows it)."""

    file: str                      # source filename (basename, kept generic)
    sheet: str                     # worksheet name
    cell: str                      # A1-style address, e.g. "B3"
    row: int                       # 1-based row number
    column: str                    # column letter, e.g. "B"
    header: Optional[str] = None   # the column's header label, if known

    def citation(self) -> str:
        """Human-readable citation, e.g. ``region_b.xlsx · Demand!C5 (Product Y)``."""
        base = f"{self.file} · {self.sheet}!{self.cell}"
        return f"{base} ({self.header})" if self.header else base


@dataclass(frozen=True)
class Value:
    """A provenance-tagged value: the number/string plus where it came from."""

    value: Any
    ref: CellRef

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "file": self.ref.file,
            "sheet": self.ref.sheet,
            "cell": self.ref.cell,
            "header": self.ref.header,
            "citation": self.ref.citation(),
        }


# --------------------------------------------------------------------------- #
# Text provenance
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PassageRef:
    """Where a text passage came from."""

    document: str                  # source filename (basename, kept generic)
    passage: int                   # 0-based passage index within the document
    kind: str = "paragraph"        # paragraph | heading | ...

    def citation(self) -> str:
        return f"{self.document} · passage {self.passage}"


@dataclass(frozen=True)
class Passage:
    """A provenance-tagged text passage (for retrieval / inquiry answers)."""

    content: str
    ref: PassageRef

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "document": self.ref.document,
            "passage": self.ref.passage,
            "kind": self.ref.kind,
            "citation": self.ref.citation(),
        }


# --------------------------------------------------------------------------- #
# A parsed table (tables-as-data; never dumped into the text index)
# --------------------------------------------------------------------------- #
@dataclass
class Table:
    """One worksheet parsed into provenance-tagged rows.

    ``rows`` is a list of dicts keyed by header label -> Value. This keeps the
    table as structured data (REP-01) rather than flattened text.
    """

    file: str
    sheet: str
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)  # list[dict[str, Value]]

    def column(self, header: str) -> list:
        """All Values under a header, in row order."""
        return [row[header] for row in self.rows if header in row]

    def cell(self, row_index: int, header: str) -> Value:
        """The Value at a given data-row index and header."""
        return self.rows[row_index][header]

    def values(self) -> list:
        """Flat list of every Value in the table."""
        out: list = []
        for row in self.rows:
            out.extend(row.values())
        return out

    def compact_summary(self, sample: int = 6) -> dict:
        """A small, provenance-carrying digest safe to pass between workflow nodes.

        Honors the inter-node size cap (research: ~80k-char limit): never ship the
        raw full table between nodes — ship shape + headers + a few sample cells.
        """
        sample_cells = [v.to_dict() for v in self.values()[:sample]]
        return {
            "file": self.file,
            "sheet": self.sheet,
            "headers": self.headers,
            "n_rows": len(self.rows),
            "sample_cells": sample_cells,
        }
