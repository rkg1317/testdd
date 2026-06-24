"""HTTP-layer smoke tests for the parser sidecar.

Closes the ENV-03 API-layer gap (RESEARCH §Wave 0 Gaps): proves /health,
/parse/excel, and /parse/memo return the expected provenance-carrying shapes
WITHOUT Docker — using FastAPI's TestClient (no network, no container).

Run:  cd app/parser_service && python -m pytest tests/test_api.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app  # the module-global FastAPI instance in app/parser_service/app.py

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Paths to pre-generated synthetic files (relative to the project root).
# The tests run from app/parser_service/ so we resolve relative to this file.
_SYNTHETIC = Path(__file__).parent.parent.parent / "synthetic_data" / "out"

REGION_A_XLSX = _SYNTHETIC / "region_a.xlsx"
MEMO_DOCX = _SYNTHETIC / "memo.docx"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok(client: TestClient) -> None:
    """GET /health must return 200 and {"status": "ok"}."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Test 2: POST /parse/excel
# ---------------------------------------------------------------------------

def test_parse_excel_returns_provenance_shape(client: TestClient) -> None:
    """POST /parse/excel with a synthetic .xlsx returns the compact_summary shape.

    Expected body keys at the top level:  file, sheets
    Each sheet summary must contain:      file, sheet, headers, n_rows, sample_cells
    Each sample_cell must contain:        file, sheet, cell, header, citation
    """
    assert REGION_A_XLSX.exists(), f"Synthetic fixture missing: {REGION_A_XLSX}"

    with open(REGION_A_XLSX, "rb") as fh:
        resp = client.post(
            "/parse/excel",
            files={"file": ("region_a.xlsx", fh, "application/octet-stream")},
        )

    assert resp.status_code == 200
    body = resp.json()

    # Top-level shape
    assert "file" in body, f"Missing 'file' key in response: {body.keys()}"
    assert "sheets" in body, f"Missing 'sheets' key in response: {body.keys()}"
    assert len(body["sheets"]) >= 1, "Expected at least one sheet"

    # Sheet summary shape
    sheet_name, summary = next(iter(body["sheets"].items()))
    for required_key in ("file", "sheet", "headers", "n_rows", "sample_cells"):
        assert required_key in summary, (
            f"Sheet summary missing '{required_key}': {summary.keys()}"
        )

    # Sample cell provenance keys
    sample_cells = summary["sample_cells"]
    assert len(sample_cells) >= 1, "Expected at least one sample cell"
    first_cell = sample_cells[0]
    for prov_key in ("file", "sheet", "cell", "header", "citation"):
        assert prov_key in first_cell, (
            f"Sample cell missing provenance key '{prov_key}': {first_cell.keys()}"
        )


# ---------------------------------------------------------------------------
# Test 3: POST /parse/memo
# ---------------------------------------------------------------------------

def test_parse_memo_returns_provenance_shape(client: TestClient) -> None:
    """POST /parse/memo with a synthetic .docx returns provenance-tagged passages.

    Expected body keys:               file, passages
    Each passage must contain:        content, document, passage
    """
    assert MEMO_DOCX.exists(), f"Synthetic fixture missing: {MEMO_DOCX}"

    with open(MEMO_DOCX, "rb") as fh:
        resp = client.post(
            "/parse/memo",
            files={"file": ("memo.docx", fh, "application/octet-stream")},
        )

    assert resp.status_code == 200
    body = resp.json()

    # Top-level shape
    assert "file" in body, f"Missing 'file' key in response: {body.keys()}"
    assert "passages" in body, f"Missing 'passages' key in response: {body.keys()}"
    assert len(body["passages"]) >= 1, "Expected at least one passage"

    # Passage provenance keys
    first_passage = body["passages"][0]
    for prov_key in ("content", "document", "passage"):
        assert prov_key in first_passage, (
            f"Passage missing provenance key '{prov_key}': {first_passage.keys()}"
        )
