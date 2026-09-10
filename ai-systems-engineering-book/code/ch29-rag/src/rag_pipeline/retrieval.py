"""Ring 6 — Retrieval: BM25 + dense 混合检索，α 加权，分数阈值供拒答判定。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .indexing import HybridIndex
from .models import Chunk


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-9)


@dataclass
class Hit:
    chunk: Chunk          # child chunk（检索单元）
    parent: Chunk | None  # parent chunk（生成注入单元，父子块折中）
    bm25_score: float     # 饱和归一 s/(s+K) ∈ [0,1)
    dense_score: float    # cosine 截断到 [0,1]
    score: float          # hybrid = alpha * bm25 + (1-alpha) * dense


def retrieve(
    query: str,
    index: HybridIndex,
    query_vec: list[float],
    *,
    top_k: int = 6,
    alpha: float = 0.6,
    bm25_saturation: float = 4.0,
) -> list[Hit]:
    bm25_raw = index.bm25.scores(query)
    hits: list[Hit] = []
    for cid, chunk in index.chunks.items():
        b = bm25_raw[cid] / (bm25_raw[cid] + bm25_saturation)
        d = max(0.0, min(1.0, cosine(query_vec, index.vectors[cid])))
        hits.append(
            Hit(
                chunk=chunk,
                parent=index.parents.get(chunk.parent_id) if chunk.parent_id else None,
                bm25_score=b,
                dense_score=d,
                score=alpha * b + (1 - alpha) * d,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:top_k]
