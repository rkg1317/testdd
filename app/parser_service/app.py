"""Parser sidecar — the custom Python tool the Dify workflow calls over HTTP.

Why a sidecar: the Dify Code-node sandbox (seccomp) blocks pandas/openpyxl, so the
deterministic file work lives here, outside the sandbox, and a workflow HTTP Request
node calls these endpoints. Portable by design — no Dify-specific code.

Run locally:  uvicorn app:app --reload --port 8000
Health check:  GET /health  ->  {"status": "ok"}
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile

from parser import parse_memo, parse_workbook

app = FastAPI(title="aipg parser sidecar", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/parse/excel")
async def parse_excel(file: UploadFile = File(...)) -> dict:
    """Parse an uploaded .xlsx -> per-sheet compact summaries (provenance-carrying)."""
    path = await _save_upload(file)
    try:
        tables = parse_workbook(path)
        return {
            "file": file.filename,
            "sheets": {name: table.compact_summary() for name, table in tables.items()},
        }
    finally:
        Path(path).unlink(missing_ok=True)


@app.post("/parse/memo")
async def parse_memo_endpoint(file: UploadFile = File(...)) -> dict:
    """Parse an uploaded .docx -> provenance-tagged passages."""
    path = await _save_upload(file)
    try:
        passages = parse_memo(path)
        return {"file": file.filename, "passages": [p.to_dict() for p in passages]}
    finally:
        Path(path).unlink(missing_ok=True)


async def _save_upload(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        return tmp.name
