"""Extract structured data from LLM text output.

Handles the three canonical failure modes demonstrated in Ch7:
1. fenced output        ```json {...}```
2. prose-wrapped output 前后夹杂说明文字
3. schema drift         field missing / wrong type / invalid enum

Truncation is NOT repairable here: finish_reason == "length" fails fast,
because retrying with more budget is a policy decision of the caller.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from .schema import TicketClassification

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass
class ExtractResult:
    ok: bool
    value: BaseModel | None
    failure: str | None  # "parse" | "validate" | "truncated" | "empty"
    error: str | None
    attempts: int


def strip_fences(text: str) -> str:
    """If the whole text (or any block) is fenced, unwrap it."""
    t = text.strip()
    m = FENCE_RE.search(t)
    if m:
        return m.group(1).strip()
    return t


def candidate_json_objects(text: str) -> list[str]:
    """Extract balanced {...} substrings, outermost first."""
    out = []
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    out.append(text[start : i + 1])
    return out


def parse_and_validate(text: str, model: type[BaseModel] = TicketClassification):
    """Try to parse text into `model`. Returns (value, failure, error)."""
    t = strip_fences(text)
    if not t:
        return None, "empty", "empty output"
    candidates = candidate_json_objects(t)
    last_err = None
    for cand in candidates:
        try:
            return model.model_validate_json(cand), None, None
        except ValidationError as e:
            last_err = ("validate", e.errors())
        except json.JSONDecodeError as e:
            last_err = ("parse", str(e))
    if last_err is None:
        return None, "parse", "no JSON object found in output"
    return None, last_err[0], json.dumps(last_err[1], ensure_ascii=False, default=str)[:500]
