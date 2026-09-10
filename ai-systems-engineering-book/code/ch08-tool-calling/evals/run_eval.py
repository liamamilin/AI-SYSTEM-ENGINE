"""Ch8 eval: tool selection + argument correctness + hallucinated-tool check.

Judges each case by running the real ToolLoop against the local model:
- tool_choice_ok   : first tool call (if any) matches expected tool
- args_ok          : declared arg_contains substrings present in arguments
- no_hallucination : no call to an unregistered tool
- answer_ok        : loop terminated with an answer (not max_rounds)
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tool_calling.client import make_client  # noqa: E402
from tool_calling.demo_tools import registry  # noqa: E402
from tool_calling.loop import ToolLoop  # noqa: E402


def judge(case: dict, out: dict) -> dict:
    expected = case["expected"]
    trace = out["tool_trace"]
    first_tool = trace[0]["tool"] if trace else None
    hallucinated = any(t["tool"] not in ("calculator", "get_weather") for t in trace)
    row = {
        "id": case["id"],
        "first_tool": first_tool,
        "tool_choice_ok": (first_tool == expected["tool"]) if expected["tool"] else (first_tool is None),
        "no_hallucination": not hallucinated,
        "answer_ok": out["stopped"] == "answer",
        "rounds": out["rounds"],
    }
    want = expected.get("arg_contains") or {}
    if want and trace:
        args = trace[0].get("args") or {}
        row["args_ok"] = all(
            str(v).replace(" ", "") in str(args.get(k, "")).replace(" ", "")
            for k, v in want.items()
        )
    else:
        row["args_ok"] = True
    return row


def main():
    here = os.path.dirname(__file__)
    cases = [json.loads(l) for l in open(os.path.join(here, "tool_cases.jsonl"), encoding="utf-8") if l.strip()]
    client = make_client(os.environ.get("LLM_PROVIDER", "ollama"))
    loop = ToolLoop(registry, max_rounds=4)

    rows = []
    for case in cases:
        out = loop.run(client, case["input"])
        rows.append(judge(case, out))

    n = len(rows)
    metrics = {
        "n": n,
        "tool_choice_accuracy": sum(r["tool_choice_ok"] for r in rows) / n,
        "args_ok_rate": sum(r["args_ok"] for r in rows) / n,
        "no_hallucination_rate": sum(r["no_hallucination"] for r in rows) / n,
        "answered_rate": sum(r["answer_ok"] for r in rows) / n,
        "first_tools": dict(Counter(str(r["first_tool"]) for r in rows)),
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    outdir = os.path.join(here, "results", ts)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(outdir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "chapter": "ch08-tool-calling",
                "model": os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx"),
                "dataset_version": "2026-09-09",
                "prompt_version": "loop-system-v1",
                "metrics": metrics,
            },
            f, ensure_ascii=False, indent=2,
        )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"results -> {outdir}")


if __name__ == "__main__":
    main()
