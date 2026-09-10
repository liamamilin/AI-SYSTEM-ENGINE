"""Unit tests for the tool-calling loop (all mocked — no LLM needed)."""

import json

from tool_calling.client import Completion
from tool_calling.demo_tools import registry
from tool_calling.loop import ToolLoop, parse_tool_call


class FakeClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete(self, messages, *, temperature=0.0, max_tokens=512):
        self.calls.append([dict(m) for m in messages])
        return Completion(text=self.outputs.pop(0), finish_reason="stop", prompt_tokens=1, completion_tokens=1)


def test_parse_plain_json():
    call = parse_tool_call('{"tool": "calculator", "arguments": {"expression": "1+2"}}')
    assert call == {"tool": "calculator", "arguments": {"expression": "1+2"}}


def test_parse_fenced_json():
    text = '好的，我来计算：\n```json\n{"tool": "calculator", "arguments": {"expression": "3*4"}}\n```'
    assert parse_tool_call(text)["arguments"]["expression"] == "3*4"


def test_parse_prose_wrapped():
    text = '查询结果如下 {"tool": "get_weather", "arguments": {"city": "上海"}} 以上。'
    assert parse_tool_call(text)["arguments"]["city"] == "上海"


def test_parse_non_tool_json_returns_none():
    assert parse_tool_call('{"foo": 1}') is None
    assert parse_tool_call("没有工具") is None


def test_registry_execute_calculator():
    r = registry.execute("calculator", {"expression": "(2+3)*4"})
    assert r.ok and r.value == 20.0


def test_registry_rejects_injection():
    r = registry.execute("calculator", {"expression": "__import__('os')"})
    assert not r.ok and "illegal" in r.error


def test_registry_unknown_tool():
    r = registry.execute("send_email", {"to": "x"})
    assert not r.ok and "unknown tool" in r.error


def test_registry_type_coercion():
    r = registry.execute("calculator", {"expression": 123})  # model sent a number
    assert r.ok and r.value == 123.0


def test_tool_error_is_data_not_crash():
    r = registry.execute("get_weather", {"city": "火星"})
    assert not r.ok and "unsupported city" in r.error
    msg = json.loads(_tool_msg(r))
    assert msg["error"]


def _tool_msg(result):
    from tool_calling.registry import tool_result_message

    return tool_result_message("get_weather", result)["content"]


def test_loop_answers_directly_without_tool():
    client = FakeClient(["北京今天 22 度，晴。"])
    loop = ToolLoop(registry, max_rounds=3)
    out = loop.run(client, "北京天气怎么样")
    assert out["stopped"] == "answer" and "22" in out["answer"]


def test_loop_uses_tool_then_answers():
    client = FakeClient(
        [
            '{"tool": "calculator", "arguments": {"expression": "128*8"}}',
            "总价是 1024 元。",
        ]
    )
    loop = ToolLoop(registry, max_rounds=4)
    out = loop.run(client, "8 台设备，单价 128，总价多少")
    assert out["stopped"] == "answer"
    assert out["tool_trace"][0]["ok"] and out["tool_trace"][0]["value"] == 1024.0
    # the tool result was fed back into the conversation
    assert any(m["role"] == "tool" for m in client.calls[-1])


def test_loop_recovers_from_tool_error():
    client = FakeClient(
        [
            '{"tool": "get_weather", "arguments": {"city": "广州"}}',
            '{"tool": "get_weather", "arguments": {"city": "深圳"}}',
            "广州不支持查询；深圳 30 度，阵雨。",
        ]
    )
    loop = ToolLoop(registry, max_rounds=5)
    out = loop.run(client, "广州和深圳的天气")
    assert out["stopped"] == "answer"
    assert out["tool_trace"][0]["ok"] is False
    assert out["tool_trace"][1]["ok"] is True


def test_loop_stops_at_max_rounds():
    client = FakeClient(['{"tool": "calculator", "arguments": {"expression": "1+1"}}'] * 10)
    loop = ToolLoop(registry, max_rounds=3)
    out = loop.run(client, "算个不停吧")
    assert out["stopped"] == "max_rounds" and len(out["tool_trace"]) == 3
