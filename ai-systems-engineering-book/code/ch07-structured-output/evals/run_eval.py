"""Ch7 eval: structured-output success rate on dataset.jsonl.

Judges (strict, auto-gradable):
- schema_ok        : output parsed & validated as TicketClassification
- category_ok      : equals expected.category
- needs_human_ok   : equals expected.needs_human
- first_pass       : succeeded on attempt 1 (no repair)

Reports first-pass rate, post-repair rate, and failure-type distribution.
Writes results to results/{ts}/ (results.jsonl + metadata.json).
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from structured_output.client import make_client  # noqa: E402
from structured_output.repair import extract_structured  # noqa: E402
from structured_output.schema import TicketClassification  # noqa: E402


def judge(value: TicketClassification | None, expected: dict, meta: dict) -> dict:
    row = {
        "id": expected["id"],
        "schema_ok": value is not None,
        "first_pass": value is not None and meta["attempts"] == 1,
        "attempts": meta["attempts"],
        "failures": meta["failures"],
        "completion_tokens": meta["usage"]["completion_tokens"],
    }
    if value is not None:
        row["category_ok"] = value.category == expected["expected"]["category"]
        row["needs_human_ok"] = value.needs_human == expected["expected"]["needs_human"]
    else:
        row["category_ok"] = False
        row["needs_human_ok"] = False
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=os.path.join(os.path.dirname(__file__), "dataset.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="limit cases (for quick smoke)")
    ap.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "ollama"))
    args = ap.parse_args()

    cases = [json.loads(line) for line in open(args.dataset, encoding="utf-8") if line.strip()]
    if args.limit:
        cases = cases[: args.limit]

    client = make_client(args.provider)
    rows = []
    t0 = time.perf_counter()
    for case in cases:
        value, meta = extract_structured(client, case["input"])
        rows.append(judge(value, case, meta))
    elapsed = time.perf_counter() - t0

    n = len(rows)
    metrics = {
        "n": n,
        "schema_ok_rate": sum(r["schema_ok"] for r in rows) / n,
        "first_pass_rate": sum(r["first_pass"] for r in rows) / n,
        "category_accuracy": sum(r["category_ok"] for r in rows) / n,
        "needs_human_accuracy": sum(r["needs_human_ok"] for r in rows) / n,
        "avg_completion_tokens": sum(r["completion_tokens"] for r in rows) / n,
        "failure_types": dict(Counter(f for r in rows for f in r["failures"])),
        "wall_seconds": round(elapsed, 1),
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    outdir = os.path.join(os.path.dirname(__file__), "results", ts)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(outdir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "chapter": "ch07-structured-output",
                "provider": args.provider,
                "model": os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx"),
                "dataset": "evals/dataset.jsonl",
                "dataset_version": "2026-09-09",
                "prompt_version": "repair-system-v1",
                "date": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
            },
            f, ensure_ascii=False, indent=2,
        )

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"results -> {outdir}")


if __name__ == "__main__":
    main()
