#!/usr/bin/env python3
"""ENV-05 tool-calling smoke test.

Sends a minimal chat/completions request with one tool definition to the
configured model endpoint and checks whether the model returns a structured
tool_calls invocation (not prose).

This is a MANUAL script — it makes a real network call and requires a valid
API key.  It is NOT run in CI.  Run it once with your key set to prove ENV-05:

    LLM_API_KEY=<your-key> python app/scripts/toolcall_smoke.py

Or with a non-default model / base URL:

    LLM_BASE_URL=https://openrouter.ai/api/v1 \
    LLM_API_KEY=<your-key> \
    LLM_MODEL=google/gemma-4-31b-it:free \
    python app/scripts/toolcall_smoke.py

Exit codes:
    0  — model returned a non-empty tool_calls array  (ENV-05 PASS)
    1  — model returned prose or no tool_calls         (ENV-05 FAIL)
    2  — network / auth / request error

Design constraint: stdlib + no new packages (uses urllib.request, json, os).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Configuration — read from environment, with DEV-ring defaults
# ---------------------------------------------------------------------------
BASE_URL: str = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
API_KEY: str = os.environ.get("LLM_API_KEY", "")
MODEL: str = os.environ.get("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

ENDPOINT = f"{BASE_URL}/chat/completions"

# ---------------------------------------------------------------------------
# Request payload — mirrors RESEARCH §ENV-05 Option B
# Prompt is a trivial arithmetic string; no file or real data sent externally.
# ---------------------------------------------------------------------------
PAYLOAD: dict = {
    "model": MODEL,
    "messages": [
        {
            "role": "user",
            "content": "What is 15 * 4? Use the calculate tool.",
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Evaluate an arithmetic expression.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The arithmetic expression to evaluate, e.g. '15 * 4'",
                        }
                    },
                    "required": ["expression"],
                },
            },
        }
    ],
    "tool_choice": "auto",
}

FALLBACK_HINT = (
    "Fallback models to try:\n"
    "  google/gemma-4-31b-it:free\n"
    "  qwen/qwen3-next-80b-a3b-instruct:free\n"
    "Also confirm that OpenRouter credits are added to your account "
    "(free-tier daily limit increases with credits, even though free models "
    "themselves are not charged)."
)


def main() -> int:
    if not API_KEY:
        print("ERROR: LLM_API_KEY is not set. Export it before running.", file=sys.stderr)
        return 2

    print(f"Sending tool-calling request to {ENDPOINT}")
    print(f"  model : {MODEL}")
    print(f"  prompt: {PAYLOAD['messages'][0]['content']}")
    print()

    data = json.dumps(PAYLOAD).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} error from endpoint:\n{raw[:500]}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 2

    # Inspect the first choice
    choices = body.get("choices", [])
    if not choices:
        print("ERROR: Response has no 'choices'.", file=sys.stderr)
        print(f"Raw response (truncated): {json.dumps(body)[:500]}", file=sys.stderr)
        return 2

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls")

    if tool_calls and len(tool_calls) > 0:
        fn = tool_calls[0].get("function", {})
        print(f"ENV-05 PASS: tool_calls present")
        print(f"  function name : {fn.get('name')}")
        print(f"  arguments     : {fn.get('arguments')}")
        return 0
    else:
        prose = message.get("content", "<no content>")
        print("ENV-05 FAIL: model did not return tool_calls (returned prose instead).")
        print(f"  model response: {str(prose)[:300]}")
        print()
        print(FALLBACK_HINT)
        return 1


if __name__ == "__main__":
    sys.exit(main())
