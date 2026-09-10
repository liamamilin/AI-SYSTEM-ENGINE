"""Ch19: an agent loop from scratch — no framework.

Agent = Model + Loop + Tools + State.
This minimal runtime adds, over Ch8's ToolLoop:
- explicit task State (progress notes, artifacts) persisted per step,
- real stop conditions (model-stopped / max-rounds / budget / stall),
- recovery from malformed proposals (bounded retries with feedback).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from tool_calling.registry import ToolRegistry, tool_result_message

TOOL_CALL_RE = re.compile(r"\{.*\}", re.DOTALL)

SYSTEM_TEMPLATE = """你是任务执行智能体。目标：{goal}

可用工具：
{tools}

你还维护一个任务状态（每步可见）：
{state}

规则：
1. 需要工具时只输出一个 JSON（无围栏）：{{"tool": "<名>", "arguments": {{...}}}}
2. 每步之后，如果你想更新任务状态，在 JSON 里加 "state_update": {{"key": "value"}}。
3. 任务完成时，输出 JSON：{{"finish": true, "answer": "<最终答复>"}}
4. 出错时读工具返回的 error，调整后再试；同样的调用不要重复超过一次。
"""


@dataclass
class AgentState:
    """Task-level state, explicitly separated from conversation history (Ch21)."""
    goal: str
    notes: dict = field(default_factory=dict)
    rounds: int = 0
    tool_calls: int = 0
    errors: list = field(default_factory=list)

    def render(self) -> str:
        return json.dumps(self.notes, ensure_ascii=False) if self.notes else "（暂无，可自行维护）"

    def apply_update(self, update: dict | None):
        if isinstance(update, dict):
            self.notes.update(update)


@dataclass
class StopReason:
    kind: str          # finished | max_rounds | max_tool_calls | stall
    answer: str | None = None


@dataclass
class AgentResult:
    answer: str | None
    stop: str
    state: AgentState
    trace: list[dict]


class AgentLoop:
    def __init__(self, registry: ToolRegistry, *, max_rounds: int = 10,
                 max_tool_calls: int = 20, max_consecutive_errors: int = 2):
        self.registry = registry
        self.max_rounds = max_rounds
        self.max_tool_calls = max_tool_calls
        self.max_consecutive_errors = max_consecutive_errors

    def run(self, client, goal: str, initial_user_input: str) -> AgentResult:
        state = AgentState(goal=goal)
        trace: list[dict] = []
        consecutive_errors = 0

        messages = [
            {"role": "system", "content": SYSTEM_TEMPLATE.format(
                goal=goal, tools=self._tool_specs(), state=state.render())},
            {"role": "user", "content": initial_user_input},
        ]

        while True:
            state.rounds += 1
            if state.rounds > self.max_rounds:
                return self._stop("max_rounds", state, trace)
            if state.tool_calls >= self.max_tool_calls:
                return self._stop("max_tool_calls", state, trace)

            completion = client.complete(messages, temperature=0.0, max_tokens=512)
            proposal = self._parse(completion.text)

            # --- finish? ---
            if proposal and proposal.get("finish"):
                return AgentResult(proposal.get("answer"), "finished", state, trace)

            # --- tool proposal ---
            if proposal and "tool" in proposal:
                name, args = proposal["tool"], proposal.get("arguments", {})
                state.tool_calls += 1
                result = self.registry.execute(name, args)
                trace.append({"round": state.rounds, "tool": name, "args": args,
                              "ok": result.ok, "value": result.value, "error": result.error})
                state.apply_update(proposal.get("state_update"))
                consecutive_errors = 0 if result.ok else consecutive_errors + 1
                if consecutive_errors >= self.max_consecutive_errors:
                    state.errors.append(f"{name}: repeated failures")
                    return self._stop("stall", state, trace)
                messages = messages + [
                    {"role": "assistant", "content": completion.text},
                    tool_result_message(name, result),
                    {"role": "user", "content": f"[状态提醒] 当前任务状态：{state.render()}"},
                ]
                continue

            # --- malformed / plain text without protocol ---
            consecutive_errors += 1
            state.errors.append("malformed_output")
            if consecutive_errors >= self.max_consecutive_errors:
                return self._stop("stall", state, trace)
            messages = messages + [
                {"role": "assistant", "content": completion.text[:500]},
                {"role": "user", "content": "请按协议输出 JSON：工具调用 / finish。"},
            ]

    def _tool_specs(self) -> str:
        return "\n".join(f"- {s['name']}: {s['description']} | {json.dumps(s['parameters'], ensure_ascii=False)}"
                         for s in self.registry.specs())

    @staticmethod
    def _parse(text: str) -> dict | None:
        t = text.strip()
        try:
            obj = json.loads(t)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            m = TOOL_CALL_RE.search(t)
            if not m:
                return None
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                return None

    def _stop(self, kind: str, state, trace) -> AgentResult:
        # graceful degradation: report partial state, never pretend success
        answer = state.notes.get("partial_answer")
        return AgentResult(answer, kind, state, trace)
