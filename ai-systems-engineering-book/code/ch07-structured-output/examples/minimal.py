"""Minimal version of Ch7: single file, shows the core loop end to end.

Run:  uv run examples/minimal.py "耳机有杂音想退货"
"""

import json
import os
import sys
import urllib.request

from pydantic import BaseModel, Field, field_validator

BASE_URL = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
MODEL = os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")
CATEGORY = ("refund", "logistics", "other")

# Note: Ollama's OpenAI-compatible endpoint ignores thinking control (verified
# 2026-09-09), so the minimal version calls the native /api/chat with think=False.
# The production path in src/ uses the client abstraction instead.

SYSTEM = (
    "你是工单分类器。只输出一个 JSON 对象："
    '{"category": "refund"|"logistics"|"other", "summary": "<=20字"}，不要输出其他内容。'
)


class Ticket(BaseModel):
    category: str
    summary: str

    @field_validator("category")
    @classmethod
    def cat_ok(cls, v):
        v = v.strip().lower()
        if v not in CATEGORY:
            raise ValueError(f"category must be one of {CATEGORY}: got {v!r}")
        return v


def extract(text: str):
    # 1) strip code fences
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").lstrip("json").strip()
    # 2) find first {...}
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        return None, "no JSON"
    # 3) validate
    try:
        return Ticket.model_validate_json(t[start : end + 1]), None
    except Exception as e:  # noqa: BLE001 - minimal version: show error to user
        return None, str(e)


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "耳机有杂音想退货"
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 200},
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read())
    value, err = extract(data.get("message", {}).get("content") or "")
    if value:
        print(json.dumps(value.model_dump(), ensure_ascii=False))
    else:
        print(f"FAILED: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
