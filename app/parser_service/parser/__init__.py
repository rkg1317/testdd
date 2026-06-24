"""Deterministic cross-file parser core.

The "correctness in code" half of the playground: precise, provenance-tagged
parsing of tabular (Excel) and text (Word/PDF) sources. Everything here is pure
Python with no LLM in the loop — the model never produces a number, it only
narrates values this layer has already computed and cited.

Lives outside the Dify Code-node sandbox (which blocks pandas/openpyxl); it is
run as a sidecar service (see ``app.py``) and called over HTTP from a workflow.
"""

from .schema import CellRef, Value, Table, PassageRef, Passage
from .excel_parser import parse_workbook
from .memo_parser import parse_memo

__all__ = [
    "CellRef",
    "Value",
    "Table",
    "PassageRef",
    "Passage",
    "parse_workbook",
    "parse_memo",
]
