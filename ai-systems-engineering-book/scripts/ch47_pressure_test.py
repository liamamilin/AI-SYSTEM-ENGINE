"""Ch47 vLLM 压测：TTFT / TPOT / 吞吐 vs 并发（Ch44 指标纪律）

对 OpenAI-compatible 端点（vLLM serve）做流式压测：
  - TTFT：首 chunk 到达时间
  - TPOT：首 token 后平均每 token 时间 = (total - ttft) / (ntok - 1)
  - 吞吐：聚合 output tokens / 墙钟
  - 每并发档 N 个请求，报告中位数/P95

用法：python3 ch47_pressure_test.py --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen2.5-7B-Instruct --levels 1,2,4,8,16,32 --reqs-per-level 16 \
  --out /root/autodl-tmp/ch47_pressure_results.json
"""
import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone

import httpx

SYSTEM = "你是资深客服。回答要点明确、编号列出、不超过 200 字。" + (
    "本系统使用统一服务话术规范：先共情，再给步骤，最后说明后续跟进方式。"
    "禁止承诺未经核实的政策细节；涉及赔偿需说明以核实结果为准。"
) * 10  # 拉长 system prompt 以体现 prefix cache 的作用
USER = "我的订单物流五天没更新了，应该怎么处理？"


async def one_request(client, base_url, model, sem, max_tokens):
    async with sem:
        t0 = time.perf_counter()
        ttft = None
        chunks = 0
        out = {"ttft": None, "tpot": None, "total": None, "tokens": 0, "ok": False}
        try:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": USER}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stream": True,
                },
                timeout=120,
            ) as r:
                r.raise_for_status()
                first_ts = None
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    delta = json.loads(payload)["choices"][0].get("delta", {})
                    if delta.get("content"):
                        now = time.perf_counter()
                        if first_ts is None:
                            first_ts = now
                            ttft = now - t0
                        else:
                            chunks += 1
                        out["tokens"] += 1
            t1 = time.perf_counter()
            out["ttft"] = round(ttft, 4)
            if chunks > 1 and first_ts is not None:
                out["tpot"] = round((t1 - first_ts) / chunks, 4)
            out["total"] = round(t1 - t0, 4)
            out["ok"] = out["tokens"] > 0
        except Exception as e:
            out["error"] = str(e)[:120]
        return out


def agg(rows, wall):
    ok = [r for r in rows if r["ok"]]
    if not ok:
        return {"success": 0}
    ttfts = sorted(r["ttft"] for r in ok)
    tpots = sorted(r["tpot"] for r in ok if r["tpot"])
    return {
        "success": len(ok),
        "ttft_median": round(statistics.median(ttfts), 4),
        "ttft_p95": round(ttfts[int(len(ttfts) * 0.95) - 1 if len(ttfts) > 1 else 0], 4),
        "tpot_median": round(statistics.median(tpots), 4) if tpots else None,
        "per_stream_tps": round(statistics.mean(r["tokens"] / r["total"] for r in ok), 1),
        "agg_throughput_tps": round(sum(r["tokens"] for r in ok) / wall, 1),
        "mean_tokens": round(statistics.mean(r["tokens"] for r in ok), 1),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--levels", default="1,2,4,8,16,32")
    ap.add_argument("--reqs-per-level", type=int, default=16)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--tag", default="")
    ap.add_argument("--out", default="/root/autodl-tmp/ch47_pressure_results.json")
    args = ap.parse_args()

    levels = [int(x) for x in args.levels.split(",")]
    results = {"meta": {"base_url": args.base_url, "model": args.model,
                        "tag": args.tag, "reqs_per_level": args.reqs_per_level,
                        "max_tokens": args.max_tokens,
                        "ts": datetime.now(timezone.utc).isoformat()},
               "levels": {}}
    async with httpx.AsyncClient() as client:
        for lvl in levels:
            print(f"[level {lvl}] running {args.reqs_per_level} requests ...")
            sem = asyncio.Semaphore(lvl)
            t0 = time.perf_counter()
            rows = await asyncio.gather(*[
                one_request(client, args.base_url, args.model, sem, args.max_tokens)
                for _ in range(args.reqs_per_level)])
            wall = time.perf_counter() - t0
            a = agg(rows, wall)
            a["wall"] = round(wall, 2)
            results["levels"][str(lvl)] = a
            print(f"  → {json.dumps(a, ensure_ascii=False)}")
    with open(args.out, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"saved → {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
