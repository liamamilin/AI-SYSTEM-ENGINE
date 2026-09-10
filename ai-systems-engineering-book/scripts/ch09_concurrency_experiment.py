"""Ch9 experiment: serial vs concurrent vs rate-limited concurrency, and TTFT.

Requires: local Ollama serving qwen3.5:9b-mlx (native /api/chat, think=False).
Measures: wall time for 6 requests under three strategies + streaming TTFT.
"""

import asyncio
import json
import os
import time
import urllib.request

BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
MODEL = os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")
PROMPTS = [
    f"用不超过15个字点评{i}：{p}" for i, p in enumerate(
        ["远程办公", "咖啡文化", "短视频", "健身", "读书", "旅行"]
    )
]


def call_once(prompt: str) -> float:
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "stream": False, "think": False, "options": {"num_predict": 60}}
    req = urllib.request.Request(
        f"{BASE}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        json.loads(r.read())
    return 0.0


async def a_call_once(prompt: str) -> None:
    await asyncio.to_thread(call_once, prompt)


async def run_serial():
    t0 = time.perf_counter()
    for p in PROMPTS:
        await a_call_once(p)
    return time.perf_counter() - t0


async def run_concurrent(n: int | None):
    sem = asyncio.Semaphore(n) if n else None

    async def guarded(p):
        if sem:
            async with sem:
                await a_call_once(p)
        else:
            await a_call_once(p)

    t0 = time.perf_counter()
    await asyncio.gather(*(guarded(p) for p in PROMPTS))
    return time.perf_counter() - t0


def ttft_stream() -> tuple[float, float]:
    """Measure TTFT (first token) and total time with streaming."""
    body = {"model": MODEL, "messages": [{"role": "user", "content": "写一首关于春天的四行小诗"}],
            "stream": True, "think": False, "options": {"num_predict": 80}}
    req = urllib.request.Request(
        f"{BASE}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft = None
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            if line.strip():
                if ttft is None:
                    ttft = time.perf_counter() - t0
                json.loads(line)
    return ttft, time.perf_counter() - t0


def main():
    print(f"model={MODEL} prompts={len(PROMPTS)}")

    async def go():
        t = await run_serial()
        print(f"serial(6):        {t:.1f}s")
        t = await run_concurrent(None)
        print(f"concurrent(6):    {t:.1f}s")
        for n in (2, 3):
            t = await run_concurrent(n)
            print(f"sem={n} concurrent: {t:.1f}s")

    asyncio.run(go())
    ttft, total = ttft_stream()
    print(f"streaming: TTFT={ttft*1000:.0f}ms  total={total*1000:.0f}ms")


if __name__ == "__main__":
    main()
