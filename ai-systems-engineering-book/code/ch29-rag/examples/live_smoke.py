"""Live smoke: 一次真实 query 走完七环并产出带引用的答案（本机 Ollama）。

Run:  cd code/ch29-rag && PYTHONPATH=src .venv/bin/python examples/live_smoke.py
Requires: Ollama running with bge-m3 + qwen3.5:9b-mlx.
"""

from __future__ import annotations

import sys

from rag_pipeline.client import OllamaClient, OllamaEmbedder
from rag_pipeline.pipeline import RagConfig, RagPipeline


def run_query(pipe: RagPipeline, query: str) -> None:
    result = pipe.answer(query)
    print(f"\n=== Query: {query} ===")
    for t in result.trace[-2:]:  # 查询期两环
        print(f"  ring {t.ring} {t.stage}: {t.summary}")
    a = result.answer
    print(f"  refused: {a.refused}")
    print(f"  answer : {a.text}")
    for c in a.citations:
        print(f"  [{c.n}] {c.source} · {c.section} (chunk {c.chunk_id})")


def main() -> None:
    embedder = OllamaEmbedder()
    llm = OllamaClient()  # 原生 /api/chat + think=False（OpenAI-compat 端点忽略 think）
    pipe = RagPipeline(embed_fn=embedder.embed, llm=llm, config=RagConfig())
    print(f"index: {len(pipe.index.chunks)} chunks, corpus_version={pipe.index.version}")
    for t in pipe.trace:
        print(f"  ring {t.ring} {t.stage}: {t.summary}")
    run_query(pipe, "会员自动续费扣款了，但我上个月就取消了订阅，怎么退款？")
    run_query(pipe, "竞品 X 的价格是多少？")


if __name__ == "__main__":
    sys.exit(main())
