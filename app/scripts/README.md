# app/scripts

Standalone utility scripts for the agentic playground.

---

## toolcall_smoke.py — ENV-05 tool-calling proof

**Purpose:** Proves that the pinned DEV model returns a structured `tool_calls`
invocation (not prose) when given a tool definition.  This de-risks the Dify
tool-calling path before any multi-step workflow is built.

This script is **not run in CI** — it makes a real network call to the
configured model endpoint and requires a valid API key.

### Run

```bash
LLM_API_KEY=<your-key> python app/scripts/toolcall_smoke.py
```

With a non-default model or base URL:

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1 \
LLM_API_KEY=<your-key> \
LLM_MODEL=google/gemma-4-31b-it:free \
python app/scripts/toolcall_smoke.py
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible base URL |
| `LLM_API_KEY`  | *(required)*                  | API key for the endpoint |
| `LLM_MODEL`    | `meta-llama/llama-3.3-70b-instruct:free` | Model ID to test |

### What to look for

**PASS line:**
```
ENV-05 PASS: tool_calls present
  function name : calculate
  arguments     : {"expression": "15 * 4"}
```

Exit code 0 = tool_calls received. ENV-05 is resolved.

**FAIL line:**
```
ENV-05 FAIL: model did not return tool_calls (returned prose instead).
```

Exit code 1. Try a fallback model (see below).

### Fallback models

If the primary model does not return `tool_calls`:

- `google/gemma-4-31b-it:free`
- `qwen/qwen3-next-80b-a3b-instruct:free`

Also confirm that OpenRouter credits are added to your account — the daily
free-tier request limit increases with credits (credits are not consumed by
free-model calls).

### Portability

The script reads only `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` from the
environment.  Point it at any OpenAI-compatible endpoint (in-house gateway,
Ollama, etc.) by changing only these variables — same script, different ring.

### Security note

The prompt sent to the endpoint is a trivial arithmetic string (`"What is
15 * 4?"`).  No file contents, no real data, no org-specific terms are ever
sent externally.  Keep this script pointed at synthetic/trivial content only.
