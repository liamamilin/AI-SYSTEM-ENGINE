"""Ch29 ring-level tests (mock only, no Ollama): rings 1-6."""

from __future__ import annotations

import math

import pytest

from rag_pipeline.chunking import chunk_structure
from rag_pipeline.cleaning import clean
from rag_pipeline.corpus import RAW_DOCS
from rag_pipeline.indexing import BM25, IndexReconcileError, build_index, reconcile, tokenize
from rag_pipeline.metadata import metadata_gate, enrich
from rag_pipeline.models import Chunk, ChunkMeta
from rag_pipeline.parsing import parse
from rag_pipeline.retrieval import cosine, retrieve

VOCAB = ["退款", "换货", "发票", "续费", "价保", "优惠券", "手机号", "闪退", "上传", "权限", "手表", "试用"]


def toy_embed_fn():
    """确定性 fake embedder：词汇表 one-hot，保证测试不依赖 Ollama。"""

    def embed(texts: list[str]) -> list[list[float]]:
        vecs = []
        for t in texts:
            v = [1.0 if w in t else 0.0 for w in VOCAB]
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vecs.append([x / norm for x in v])
        return vecs

    return embed


def build_toy_index():
    children: list[Chunk] = []
    parents: list[Chunk] = []
    for raw in RAW_DOCS:
        doc = clean(parse(raw))
        cs, ps = chunk_structure(doc)
        enrich(cs, doc)
        children += cs
        parents += ps
    accepted, rejected = metadata_gate(children)
    assert not rejected
    return build_index(accepted, parents, toy_embed_fn())


# Ring 2 — Cleaning
def test_clean_strips_headers_footers_and_mojibake():
    doc = clean(parse(RAW_DOCS[0]))
    assert "【客服知识库" not in doc.text
    assert "第 1 页 / 共 2 页" not in doc.text
    assert "打印无效" not in doc.text
    assert "退款流程" in doc.text


# Ring 3 — Chunking（结构对齐 + 父子块）
def test_chunking_respects_section_boundaries_and_parent_link():
    doc = clean(parse(RAW_DOCS[0]))
    children, parents = chunk_structure(doc)
    assert children and parents
    parent_ids = {p.chunk_id for p in parents}
    sections = {p.section: p.text for p in parents}
    for c in children:
        assert c.parent_id in parent_ids  # 每个 child 都有 parent
        assert c.text in sections[c.section]  # child 不跨章节边界
    assert any("退款流程" in p.section for p in parents)


# Ring 4 — Metadata 门禁
def test_metadata_gate_rejects_chunks_missing_source_or_date():
    ok = Chunk(chunk_id="a", doc_id="d", text="x", meta=ChunkMeta(source="f.md", section="s", date="2026-06-01"))
    no_date = Chunk(chunk_id="b", doc_id="d", text="y", meta=ChunkMeta(source="f.md", section="s", date=""))
    no_meta = Chunk(chunk_id="c", doc_id="d", text="z")
    accepted, rejected = metadata_gate([ok, no_date, no_meta])
    assert accepted == [ok]
    assert set(c.chunk_id for c in rejected) == {"b", "c"}


# Ring 5 — 索引/语料对账
def test_reconcile_detects_index_corpus_mismatch():
    index = build_toy_index()
    reconcile(index, len(index.chunks), 7)  # 一致 → 通过
    with pytest.raises(IndexReconcileError):
        reconcile(index, len(index.chunks) + 1, 7)
    with pytest.raises(IndexReconcileError):
        reconcile(index, len(index.chunks), 8)  # 版本不配对（陈旧索引）


# Ring 5/6 — BM25 + tokenize
def test_bm25_ranks_relevant_chunk_first():
    index = build_toy_index()
    scores = index.bm25.scores("怎么申请退款")
    top = max(scores, key=lambda k: scores[k])
    assert index.chunks[top].meta.source == "kb_refund_policy.md"  # type: ignore[union-attr]


def test_tokenize_char_bigram_for_chinese():
    assert tokenize("退款refund") == ["退款", "refund"]


# Ring 6 — 混合检索 α 加权
def test_hybrid_alpha_weighting():
    index = build_toy_index()
    q = "怎么申请退款"
    qv = toy_embed_fn()([q])[0]
    pure_bm25 = retrieve(q, index, qv, alpha=1.0, top_k=99)
    pure_dense = retrieve(q, index, qv, alpha=0.0, top_k=99)
    assert [h.chunk.chunk_id for h in pure_bm25] == sorted(
        index.chunks, key=lambda i: -index.bm25.scores(q)[i]
    )
    assert [h.chunk.chunk_id for h in pure_dense] == sorted(
        index.chunks, key=lambda i: -cosine(qv, index.vectors[i])
    )
    blend = retrieve(q, index, qv, alpha=0.6, top_k=99)
    for h in blend:
        expected = 0.6 * h.bm25_score + 0.4 * h.dense_score
        assert abs(h.score - expected) < 1e-9  # hybrid = α·bm25 + (1-α)·dense


def test_dense_scores_zero_for_out_of_domain_query():
    index = build_toy_index()
    qv = toy_embed_fn()(["竞品X的价格是多少"])[0]
    hits = retrieve("竞品X的价格是多少", index, qv, top_k=99, alpha=0.6)
    assert all(h.dense_score == 0.0 for h in hits)
    assert all(h.score < 0.45 for h in hits)  # 低于默认拒答阈值
