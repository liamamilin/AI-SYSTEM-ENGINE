"""Metrics: auto-gradable primitives shared by all chapter evals."""

from __future__ import annotations

from collections import Counter


def rates(rows: list[dict], keys: list[str]) -> dict:
    n = len(rows) or 1
    return {k: sum(1 for r in rows if r.get(k)) / n for k in keys}


def failure_distribution(rows: list[dict], field: str = "failures") -> dict:
    return dict(Counter(f for r in rows for f in (r.get(field) or [])))


def p_percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, round(p / 100 * (len(s) - 1))))
    return s[idx]


def latency_summary(latencies_ms: list[float]) -> dict:
    return {"p50": round(p_percentile(latencies_ms, 50), 1),
            "p95": round(p_percentile(latencies_ms, 95), 1),
            "p99": round(p_percentile(latencies_ms, 99), 1)}


def exact_match(pred: str, expected: str) -> bool:
    return pred.strip() == expected.strip()


def contains_any(pred: str, options: list[str]) -> bool:
    return any(opt in pred for opt in options)
