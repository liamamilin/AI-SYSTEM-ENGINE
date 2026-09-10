"""Tests for the shared eval runner (no LLM)."""

import json

from eval_runner.dataset import load_dataset
from eval_runner.metrics import failure_distribution, latency_summary, p_percentile, rates
from eval_runner.runner import run_eval


class C:
    def __init__(self, id, input, expected, metadata=None):
        self.id, self.input, self.expected, self.metadata = id, input, expected, metadata or {}


def test_dataset_load_and_version(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text(json.dumps({"id": "a", "input": "x", "expected": {"y": 1}}, ensure_ascii=False) + "\n"
                 + json.dumps({"id": "b", "input": "z", "expected": {"y": 2}}, ensure_ascii=False) + "\n", encoding="utf-8")
    cases, info = load_dataset(str(p))
    assert len(cases) == 2 and info["n"] == 2 and len(info["sha256_12"]) == 12


def test_dataset_bad_line_fails_loudly(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text('{"id": "a", "input": "x"}\n', encoding="utf-8")  # missing expected
    try:
        load_dataset(str(p))
        assert False, "should raise"
    except ValueError as e:
        assert "expected" in str(e)


def test_runner_isolates_failures():
    cases = [C("a", "1", {}), C("b", "2", {}), C("c", "3", {})]

    def fn(case):
        if case.id == "b":
            raise RuntimeError("boom")
        return {"id": case.id, "ok": True}

    rows, meta = run_eval(cases, fn)
    assert len(rows) == 3
    assert meta["n_failed_execution"] == 1
    bad = [r for r in rows if r.get("execution_error")]
    assert bad[0]["id"] == "b" and "boom" in bad[0]["execution_error"]


def test_metrics_primitives():
    rows = [{"ok": True}, {"ok": False}, {"ok": True}]
    assert rates(rows, ["ok"])["ok"] == 2 / 3
    assert p_percentile([1, 2, 3, 4, 100], 50) == 3
    s = latency_summary([10, 20, 30, 100, 200])
    assert s["p50"] <= s["p95"] <= s["p99"]
    assert failure_distribution([{"failures": ["parse"]}, {"failures": ["parse", "validate"]}]) == {"parse": 2, "validate": 1}
