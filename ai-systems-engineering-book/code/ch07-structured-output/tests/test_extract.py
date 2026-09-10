"""Unit tests for extraction and repair logic (no LLM required — fake client)."""

import json

import pytest
from pydantic import BaseModel

from structured_output.client import Completion
from structured_output.extract import candidate_json_objects, parse_and_validate, strip_fences
from structured_output.repair import extract_structured
from structured_output.schema import TicketClassification

VALID = json.dumps(
    {"category": "refund", "urgency": "medium", "summary": "耳机有杂音想退货", "needs_human": False},
    ensure_ascii=False,
)


class FakeClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete(self, messages, *, temperature=0.0, max_tokens=512):
        self.calls.append([dict(m) for m in messages])
        return Completion(text=self.outputs.pop(0), finish_reason="stop", prompt_tokens=10, completion_tokens=20)


def test_strip_fences():
    assert strip_fences(f"```json\n{VALID}\n```") == VALID
    assert strip_fences(VALID) == VALID


def test_candidate_json_objects_prose_wrapped():
    text = f"分类结果如下：{VALID}。请查收。"
    objs = candidate_json_objects(text)
    assert len(objs) == 1
    value, failure, _ = parse_and_validate(text)
    assert value is not None and failure is None


def test_parse_failure_prose_only():
    value, failure, _ = parse_and_validate("我觉得应该归为退款类。")
    assert value is None and failure == "parse"


def test_validate_failure_bad_enum():
    bad = json.dumps({"category": "退货退款", "urgency": "medium", "summary": "x", "needs_human": False}, ensure_ascii=False)
    value, failure, error = parse_and_validate(bad)
    assert value is None and failure == "validate" and "category" in error


def test_validate_failure_missing_field():
    bad = json.dumps({"category": "refund", "summary": "x"}, ensure_ascii=False)
    value, failure, _ = parse_and_validate(bad)
    assert value is None and failure == "validate"


def test_repair_recovers_after_feedback():
    client = FakeClient(["这不是JSON，直接回答：属于退款", f"```json\n{VALID}\n```"])
    value, meta = extract_structured(client, "耳机坏了")
    assert value is not None
    assert meta["attempts"] == 2
    assert meta["failures"] == ["parse"]
    # error feedback was injected into the conversation
    last_user = client.calls[-1][-1]["content"]
    assert "不符合 schema" in last_user


def test_repair_gives_up_after_max_attempts():
    client = FakeClient(["no json", "still no json", "nope"])
    value, meta = extract_structured(client, "耳机坏了", max_attempts=3)
    assert value is None
    assert meta["attempts"] == 3
    assert len(meta["failures"]) == 3


def test_truncation_fails_fast_not_repaired():
    class TruncClient(FakeClient):
        def complete(self, messages, *, temperature=0.0, max_tokens=512):
            self.calls.append(messages)
            return Completion(text="", finish_reason="length", prompt_tokens=1, completion_tokens=max_tokens)

    client = TruncClient([])
    value, meta = extract_structured(client, "耳机坏了")
    assert value is None
    assert meta["failures"] == ["truncated"]
    assert meta["attempts"] == 1  # no wasted retry on truncation


def test_summary_length_validation():
    long_summary = "很" * 60
    bad = json.dumps({"category": "refund", "urgency": "low", "summary": long_summary, "needs_human": False}, ensure_ascii=False)
    value, failure, error = parse_and_validate(bad)
    assert value is None and failure == "validate" and "summary" in error
