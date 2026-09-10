"""Ch41/44 experiment: measure TTFT vs context length and decode speed locally.

Uses Ollama streaming (native API, think=False) on the local model.
Demonstrates: context length -> TTFT growth (prefill cost), tokens/s (decode).
"""

import json
import os
import time
import urllib.request

BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
MODEL = os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")

PAD = "这是一段填充文本，用于增加上下文长度。机器学习系统需要考虑延迟与成本的权衡。" * 60  # ~150 tokens/pad unit


def stream_call(prompt: str):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "stream": True, "think": False, "options": {"num_predict": 100}}
    req = urllib.request.Request(f"{BASE}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft = None
    gen_chunks = 0
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            if not line.strip():
                continue
            data = json.loads(line)
            content = data.get("message", {}).get("content") or ""
            if content:
                gen_chunks += 1
                if ttft is None:
                    ttft = time.perf_counter() - t0
            if data.get("done"):
                pt = data.get("prompt_eval_count", 0)
                prefill_ms = data.get("prompt_eval_duration", 0) / 1e6
    total = time.perf_counter() - t0
    gen_after_ttft = total - (ttft or total)
    return {"ttft_s": round(ttft, 3) if ttft else -1, "total_s": round(total, 3),
            "prompt_tokens": pt, "prefill_ms": round(prefill_ms, 1),
            "gen_tokens": gen_chunks, "gen_tps": round(gen_chunks / gen_after_ttft, 1) if gen_after_ttft > 0 else 0}


def main():
    import random
    for pads in [0, 1, 4, 12]:
        salt = f"[run-{random.randint(0, 10**9)}]\n"   # 打破前缀缓存，取独立 prefill
        prompt = salt + (PAD * pads) + "\n\n用一句话总结上面的内容要点。"
        r = stream_call(prompt)
        print(f"context≈{r['prompt_tokens']:5d} tok | TTFT={r['ttft_s']:6.3f}s "
              f"| prefill={r['prefill_ms']:7.1f}ms | gen={r['gen_tps']:5.1f} tok/s")


if __name__ == "__main__":
    main()
