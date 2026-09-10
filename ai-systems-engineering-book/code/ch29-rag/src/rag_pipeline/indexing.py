"""Ring 5 — Indexing: BM25 倒排 + 向量索引 + 索引/语料对账。"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .models import Chunk

EmbedFn = object  # Callable[[list[str]], list[list[float]]]

TOKEN_HAN = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """字符 bigram（中文）+ 连续 latin/digit 词（同 ch28 实验脚本，确定性）。"""
    toks: list[str] = []
    for han in TOKEN_HAN.findall(text):
        toks += [han[i:i + 2] for i in range(len(han) - 1)]
    toks += re.findall(r"[a-zA-Z0-9]+", text)
    return toks


class BM25:
    """Okapi BM25（k1=1.5, b=0.75），语料为 chunk_id → text。"""

    def __init__(self, docs: dict[str, str], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.dts = {i: tokenize(d) for i, d in docs.items()}
        self.dl = {i: len(t) for i, t in self.dts.items()}
        self.avgdl = sum(self.dl.values()) / len(docs) if docs else 0.0
        self.df: dict[str, int] = {}
        for toks in self.dts.values():
            for t in set(toks):
                self.df[t] = self.df.get(t, 0) + 1

    def score(self, query: str, doc_id: str) -> float:
        toks, dl, s = self.dts[doc_id], self.dl[doc_id], 0.0
        tf: dict[str, int] = {}
        for t in tokenize(query):
            tf[t] = tf.get(t, 0) + 1
        n = len(self.docs)
        for t in tf:
            if t not in self.df:
                continue
            idf = math.log((n - self.df[t] + 0.5) / (self.df[t] + 0.5) + 1)
            f = toks.count(t)
            s += idf * (f * (self.k1 + 1)) / (
                f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            )
        return s

    def scores(self, query: str) -> dict[str, float]:
        return {i: self.score(query, i) for i in self.docs}


@dataclass
class HybridIndex:
    chunks: dict[str, Chunk]          # child chunks（检索单元）
    parents: dict[str, Chunk]         # parent chunks（生成注入单元）
    vectors: dict[str, list[float]]   # child chunk embeddings
    bm25: BM25
    version: int = 1


class IndexReconcileError(RuntimeError):
    """索引/语料对账失败（文档数或版本不一致——索引静默腐烂的显式告警）。"""


def reconcile(index: HybridIndex, n_docs: int, corpus_version: int) -> None:
    versions = {c.meta.version for c in index.chunks.values() if c.meta}
    if len(index.chunks) != n_docs or versions - {corpus_version}:
        raise IndexReconcileError(
            f"index/corpus mismatch: index={len(index.chunks)} corpus={n_docs}, "
            f"index_versions={sorted(versions)} corpus_version={corpus_version}"
        )


def build_index(
    children: list[Chunk],
    parents: list[Chunk],
    embed_fn: EmbedFn,
    corpus_version: int = 1,
) -> HybridIndex:
    chunks = {c.chunk_id: c for c in children}
    vectors = embed_fn([c.text for c in children])
    return HybridIndex(
        chunks=chunks,
        parents={p.chunk_id: p for p in parents},
        vectors=dict(zip(chunks, vectors, strict=True)),
        bm25=BM25({i: c.text for i, c in chunks.items()}),
        version=corpus_version,
    )
