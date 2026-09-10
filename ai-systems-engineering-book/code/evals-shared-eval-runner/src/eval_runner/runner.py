"""Runner: execute cases with failure isolation + reproducible metadata (Ch17).

Writes results/{run_id}/ with results.jsonl + metadata.json
(metadata includes model/prompt/dataset versions + timestamp — the minimum
required for any run to be comparable later).
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone


def run_eval(
    cases,
    executor_fn,  # case -> dict row (must include "id")
    *,
    concurrency: int = 1,
    out_dir: str | None = None,
    metadata: dict | None = None,
) -> tuple[list[dict], dict]:
    rows = []
    latencies = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = {pool.submit(_guarded, c, executor_fn): c for c in cases}
        for fut in as_completed(futs):
            row = fut.result()
            rows.append(row)
            if "latency_ms" in row:
                latencies.append(row["latency_ms"])
    rows.sort(key=lambda r: r["id"])

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    meta = {
        "run_id": run_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "n_cases": len(rows),
        "n_failed_execution": sum(1 for r in rows if r.get("execution_error")),
        **(metadata or {}),
    }
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "results.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    return rows, meta


def _guarded(case, executor_fn) -> dict:
    """Failure isolation: one bad case never kills the batch (Ch9 lesson)."""
    t0 = time.perf_counter()
    try:
        row = executor_fn(case)
        row["id"] = row.get("id", case.id)
        row["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return row
    except Exception as e:  # noqa: BLE001
        return {"id": case.id, "execution_error": f"{type(e).__name__}: {e}",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
