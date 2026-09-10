"""Repair loop: validation failure -> error feedback -> bounded retry.

Policy (Ch7):
- parse/validate failures are repairable: re-ask with the schema + the error.
- truncation (finish_reason == "length") is NOT auto-repaired here; caller
  decides whether to raise budget (it costs money) — we surface it explicitly.
- max_attempts bounds the total cost; default 2 extra attempts.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from .client import Completion, LLMClient
from .extract import parse_and_validate
from .schema import TicketClassification, schema_hint

SYSTEM_TEMPLATE = """你是工单结构化提取器。

[schema]
{schema}

[规则]
- 只输出一个 JSON 对象，不加围栏、不加解释。
- 字段值必须严格遵守 schema 的取值范围与类型。
"""


def extract_structured(
    client: LLMClient,
    user_input: str,
    *,
    model: type[BaseModel] = TicketClassification,
    max_attempts: int = 3,
    max_tokens: int = 512,
) -> tuple[BaseModel | None, dict]:
    """Returns (result | None, meta) where meta records the repair trail."""
    system = SYSTEM_TEMPLATE.format(schema=schema_hint())
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"<ticket>\n{user_input}\n</ticket>"},
    ]
    meta = {"attempts": 0, "failures": [], "usage": {"prompt_tokens": 0, "completion_tokens": 0}}

    for attempt in range(1, max_attempts + 1):
        meta["attempts"] = attempt
        completion: Completion = client.complete(messages, temperature=0.0, max_tokens=max_tokens)
        meta["usage"]["prompt_tokens"] += completion.prompt_tokens
        meta["usage"]["completion_tokens"] += completion.completion_tokens

        if completion.finish_reason == "length":
            meta["failures"].append("truncated")
            return None, meta  # not repairable within this policy

        value, failure, error = parse_and_validate(completion.text, model)
        if value is not None:
            return value, meta

        meta["failures"].append(failure)
        # error-feedback repair: show the model exactly what was wrong
        messages = messages[:2] + [
            {"role": "assistant", "content": completion.text[:1000]},
            {
                "role": "user",
                "content": (
                    f"你的输出不符合 schema，错误：\n{error}\n"
                    f"请重新输出一个完全符合 schema 的 JSON 对象（只输出 JSON）。\n"
                    f"schema:\n{schema_hint()}"
                ),
            },
        ]

    return None, meta


def result_to_dict(value: BaseModel | None) -> dict | None:
    if value is None:
        return None
    return json.loads(value.model_dump_json())
