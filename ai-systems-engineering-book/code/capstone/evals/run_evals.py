"""Ch60 capstone — evals runner（接入 evals-shared-eval-runner，Ch13/17）。

分层评测（mock 模式）：检索/权限/SQL/拒答层是确定性组件评测（不依赖模型）；
生成质量（faithfulness/引用正确性）需要 live 模式——mock 模式如实只评
可确定性的层，metadata.mode=mock 明示。落盘 results/{run_id}/。
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_CODE = os.path.dirname(_ROOT)
for p in (
    os.path.join(_ROOT, "src"),
    os.path.join(_CODE, "ch08-tool-calling", "src"),
    os.path.join(_CODE, "ch11-model-gateway", "src"),
    os.path.join(_CODE, "ch19-agent-loop", "src"),
    os.path.join(_CODE, "ch29-rag", "src"),
    os.path.join(_CODE, "ch33-ai-backend", "src"),
    os.path.join(_CODE, "evals-shared-eval-runner", "src"),
):
    if p not in sys.path:
        sys.path.insert(0, p)

from capstone.platform import KnowledgePlatform, toy_embed_fn  # noqa: E402
from capstone.security import UserContext  # noqa: E402
from capstone.tools import ToolHost  # noqa: E402

from eval_runner.dataset import load_dataset  # noqa: E402
from eval_runner.metrics import latency_summary, rates  # noqa: E402
from eval_runner.runner import run_eval  # noqa: E402

USERS = {
    "it_alice": UserContext(user_id="u001", clearance="internal", departments={"it"}, role="employee"),
    "hr_bob": UserContext(user_id="u002", clearance="confidential", departments={"hr"}, role="approver"),
    "guest": UserContext(user_id="u003", clearance="public", departments={"sales"}, role="guest"),
    "finance_carol": UserContext(user_id="u004", clearance="internal", departments={"finance"}, role="employee"),
}


def make_mock_platform() -> KnowledgePlatform:
    return KnowledgePlatform(embed_fn=toy_embed_fn(), llm=None)


def execute_case(case, platform: KnowledgePlatform) -> dict:
    user = USERS[case.metadata.get("user", "it_alice")]
    layer = case.metadata.get("layer", "?")
    failures: list[str] = []
    if layer in ("simple_fact", "multi_hop"):
        out = platform.search(user, case.input)
        got = set(out.allowed_ids)
        want = set(case.expected["docs"])
        if not want <= got:
            failures.append(f"retrieval_miss: want={sorted(want)} got={sorted(got)} (denied={out.denied_ids})")
    elif layer == "refuse":
        out = platform.answer(user, case.input)
        if not (out.refused and out.stop != "degraded_job_queued"):
            failures.append(f"should_refuse: refused={out.refused} stop={out.stop} answer={(out.answer or '')[:60]!r}")
    elif layer == "permission":
        out = platform.search(user, case.input)
        denied = case.expected["doc"] in out.denied_ids
        if case.expected["denied"] and not denied:
            failures.append(f"acl_leak: {case.expected['doc']} 可见（越权）")
        if not case.expected["denied"] and case.expected["doc"] not in out.allowed_ids:
            failures.append(f"acl_overblock: {case.expected['doc']} 应可见被拒")
    elif layer == "sql":
        host = ToolHost(platform, user)
        try:
            host.query_db(case.input)
            ok = True
            reason = None
        except Exception as e:  # noqa: BLE001
            ok = False
            reason = "readonly" if "只读" in str(e) else ("multi_statement" if "多语句" in str(e) else "unknown_table")
        if ok != case.expected["ok"]:
            failures.append(f"sql_expectation: want ok={case.expected['ok']} got={ok} ({reason})")
        if not ok and case.expected.get("reason") and reason != case.expected["reason"]:
            failures.append(f"sql_reason: want={case.expected['reason']} got={reason}")
    else:
        failures.append(f"unknown_layer: {layer}")
    return {"id": case.id, "layer": layer, "pass": not failures, "failures": failures}


def main() -> int:
    dataset_path = os.path.join(_HERE, "dataset.jsonl")
    cases, info = load_dataset(dataset_path)
    platform = make_mock_platform()
    rows, meta = run_eval(
        cases,
        lambda c: execute_case(c, platform),
        out_dir=os.path.join(_ROOT, "results", "mock-latest"),
        metadata={
            "mode": "mock",
            "dataset": info,
            "note": "mock 模式：检索/权限/SQL/拒答为确定性组件评测；生成质量需 live 模式",
        },
    )
    layers: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        layers[r["layer"]].append(r)
    print(f"capstone evals — dataset={info['n']} cases sha={info['sha256_12']} mode=mock")
    print(f"{'layer':<20}{'n':>4}{'pass_rate':>12}")
    for layer in sorted(layers):
        rs = layers[layer]
        rate = rates(rs, ["pass"])["pass"]
        print(f"{layer:<20}{len(rs):>4}{rate:>11.0%}")
    overall = rates(rows, ["pass"])["pass"]
    lat = latency_summary([r["latency_ms"] for r in rows])
    print(f"{'OVERALL':<20}{len(rows):>4}{overall:>11.0%}   latency p50/p95={lat['p50']}/{lat['p95']}ms")
    print("results → code/capstone/results/mock-latest/ (results.jsonl + metadata.json)")
    return 0 if overall == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
