"""The tool-calling loop: propose -> validate -> execute -> feed back -> repeat.

Key design points (Ch8):
- the model proposes; the host executes (never let the model "run" anything);
- tool errors are serialized as DATA back to the model (structured, teachable),
  not stack traces;
- max_rounds bounds runaway loops (Ch19 replaces this with a real stop-condition
  policy; here it is a guardrail).
"""

from __future__ import annotations

import json
import re

from .registry import ToolRegistry, tool_result_message

TOOL_CALL_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_tool_call(text: str) -> dict | None:
    """Extract a {"tool": name, "arguments": {...}} proposal from model text."""
    t = text.strip()
    candidates: list[str] = []
    m = TOOL_CALL_RE.search(t)
    if m:
        candidates.append(m.group(1))
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        candidates.append(t[start : end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and "tool" in obj:
                return {"tool": obj["tool"], "arguments": obj.get("arguments", {})}
        except json.JSONDecodeError:
            continue
    return None


SYSTEM_TEMPLATE = """你是任务执行助手。你可以使用以下工具：

{tools}

规则：
1. 需要工具时，只输出一个 JSON 对象（不要围栏）：
   {{"tool": "<工具名>", "arguments": {{...}}}}
2. arguments 的键名和取值类型必须严格符合工具的 parameters 描述。
3. 工具执行结果会以 JSON 回注给你；如果结果包含 "error"，请根据错误调整你的下一次调用或直接回答用户。
4. 信息足够回答时，不要再调用工具，直接输出最终答案（不要 JSON）。
"""


class ToolLoop:
    def __init__(self, registry: ToolRegistry, max_rounds: int = 6):
        self.registry = registry
        self.max_rounds = max_rounds

    def run(self, client, user_input: str) -> dict:
        """Returns {"answer": str|None, "rounds": int, "tool_trace": [...], "stopped": str}"""
        system = SYSTEM_TEMPLATE.format(
            tools="\n".join(
                f"- {s['name']}: {s['description']} | 参数: {json.dumps(s['parameters'], ensure_ascii=False)}"
                for s in self.registry.specs()
            )
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ]
        trace: list[dict] = []
        for round_no in range(1, self.max_rounds + 1):
            completion = client.complete(messages, temperature=0.0, max_tokens=512)
            call = parse_tool_call(completion.text)
            if call is None:
                return {
                    "answer": completion.text.strip(),
                    "rounds": round_no,
                    "tool_trace": trace,
                    "stopped": "answer",
                }
            name, args = call["tool"], call["arguments"]
            result = self.registry.execute(name, args)
            trace.append({"round": round_no, "tool": name, "args": args,
                          "ok": result.ok, "value": result.value, "error": result.error})
            messages = messages + [
                {"role": "assistant", "content": completion.text},
                tool_result_message(name, result),
            ]
        return {"answer": None, "rounds": self.max_rounds, "tool_trace": trace,
                "stopped": "max_rounds"}
