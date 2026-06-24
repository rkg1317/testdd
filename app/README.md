# app/ — buildable code for the cross-file PoC

Generic, portable, push-anywhere code for the AI Playground PoC. No org or
proprietary terms. The Dify workflows orchestrate; the precise file work lives
here in plain Python (run as a sidecar service the workflow calls over HTTP).

## Layout

| Path | What |
|------|------|
| `parser_service/` | The deterministic parser — citation schema + Excel/memo parsers + a FastAPI sidecar (`app.py`) + `Dockerfile`. Runs *outside* the Dify sandbox. |
| `synthetic_data/` | `generate.py` — produces the fully-generic fixtures (Region A/B/C Excels + a Word memo), engineered so the demo question has a clean answer. |
| `.env.example` | Model-ring config ("swap the URL") — copy to `.env`. |

## Why a sidecar (the key design decision)

Research confirmed the Dify Code-node sandbox (seccomp) **blocks pandas / openpyxl /
matplotlib**. Rather than patch the sandbox, the deterministic file work runs in a
separate container and a Dify **HTTP Request** node calls it. This keeps correctness
in code, stays portable, and sidesteps the sandbox entirely.

## Quickstart (local, no Docker, no GPU)

```bash
cd app/parser_service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# generate the synthetic fixtures
python ../synthetic_data/generate.py        # writes ../synthetic_data/out/

# run the tests (citation schema + parsers)
python -m pytest -q

# (optional) run the sidecar
uvicorn app:app --reload --port 8000        # GET /health -> {"status":"ok"}
```

## Status

- ✅ Citation schema (`{value, file, sheet, cell}` / `{content, document, passage}`)
- ✅ Deterministic Excel parser (cell-address provenance) + Word memo parser
- ✅ Synthetic fixtures (purpose-built for the QoQ-drop demo)
- ✅ FastAPI sidecar shell (`/health`, `/parse/excel`, `/parse/memo`) + Dockerfile
- ⏳ Compute + chart (pandas/matplotlib), PDF (pdfplumber), and the Dify workflow
  graph land in their roadmap phases (see `../.planning/ROADMAP.md`).
