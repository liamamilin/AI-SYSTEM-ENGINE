"""Tests for the from-scratch agent loop (mocked client — deterministic)."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ch08-tool-calling", "src"))

from agent_loop import AgentLoop
from tool_calling.client import Completion
from tool_calling.demo_tools import registry


class ScriptedClient:
    """Plays back scripted outputs; records the conversation."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete(self, messages, *, temperature=0.0, max_tokens=512):
        self.calls.append([dict(m) for m in messages])
        return Completion(text=self.outputs.pop(0), finish_reason="stop", prompt_tokens=1, completion_tokens=1)


def J(**kw):
    return json.dumps(kw, ensure_ascii=False)


def test_finish_immediately():
    client = ScriptedClient([J(finish=True, answer="完成了")])
    out = AgentLoop(registry).run(client, "目标", "输入")
    assert out.stop == "finished" and out.answer == "完成了"


def test_tool_then_finish_state_tracked():
    client = ScriptedClient(
        [
            J(tool="calculator", arguments={"expression": "2+3"}, state_update={"计算": "已算2+3"}),
            J(finish=True, answer="5"),
        ]
    )
    out = AgentLoop(registry, max_rounds=5).run(client, "算 2+3", "算一下")
    assert out.stop == "finished" and out.answer == "5"
    assert out.state.notes["计算"] == "已算2+3"
    assert out.state.tool_calls == 1
    assert out.trace[0]["value"] == 5.0
    # state was injected back into the conversation (visible next round)
    last_user = [m for m in client.calls[-1] if m["role"] == "user"][-1]["content"]
    assert "已算2+3" in last_user


def test_stall_on_repeated_tool_errors():
    outputs = [J(tool="get_weather", arguments={"city": "火星"}) for _ in range(5)]
    client = ScriptedClient(outputs)
    out = AgentLoop(registry, max_rounds=10).run(client, "查火星天气", "查")
    assert out.stop == "stall"
    assert out.answer is None  # never pretend success
    assert any("get_weather" in e for e in out.state.errors)


def test_stall_on_repeated_malformed_output():
    client = ScriptedClient(["我就随便说说", "还是随便说说", "继续说"])
    out = AgentLoop(registry, max_rounds=10).run(client, "目标", "输入")
    assert out.stop == "stall"


def test_max_rounds_bound():
    outputs = [J(tool="calculator", arguments={"expression": f"{i}+1"}) for i in range(20)]
    client = ScriptedClient(outputs)
    out = AgentLoop(registry, max_rounds=4).run(client, "数数", "输入")
    assert out.stop == "max_rounds"
    assert out.state.rounds == 5


def test_max_tool_calls_bound():
    outputs = [J(tool="calculator", arguments={"expression": "1+1"}) for _ in range(30)]
    client = ScriptedClient(outputs)
    out = AgentLoop(registry, max_rounds=50, max_tool_calls=3).run(client, "目标", "输入")
    assert out.stop == "max_tool_calls"


def test_recovers_after_one_malformed_step():
    client = ScriptedClient(
        ["好的我来算一下"],  # not protocol
    )
    client2 = ScriptedClient(
        ["好的我来算一下", J(tool="calculator", arguments={"expression": "1+1"}), J(finish=True, answer="2")]
    )
    out = AgentLoop(registry, max_rounds=5).run(client2, "算 1+1", "输入")
    assert out.stop == "finished" and out.answer == "2"
    assert out.state.errors.count("malformed_output") == 1  # recovered once
