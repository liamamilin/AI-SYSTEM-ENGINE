"""Seven-ring pipeline orchestration: build (rings 1-5) + answer (rings 6-7).

管道原则：任何一环都可以被 mock 掉做下游评测——
评测生成时冻结检索（answer_with_frozen_hits），评测检索时不需要生成。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from .chunking import chunk_structure
from .cleaning import clean
from .client import LLMClient
from .corpus import RAW_DOCS, RawDoc
from .generation import Answer, generate, refuse
from .indexing import HybridIndex, build_index, reconcile
from .metadata import enrich, metadata_gate
from .models import Chunk, RingTrace
from .parsing import parse
from .retrieval import Hit, retrieve

RING_STAGES = ["parsing", "cleaning", "chunking", "metadata", "indexing", "retrieval", "generation"]


class RagConfig(BaseModel):
    top_k: int = 6
    alpha: float = 0.6
    refuse_threshold: float = 0.45
    bm25_saturation: float = 4.0
    max_tokens: int = 512
    corpus_version: int = 7


@dataclass
class RagResult:
    answer: Answer
    trace: list[RingTrace] = field(default_factory=list)


@dataclass
class RagPipeline:
    """索引在构造时建立（rings 1-5），查询走 rings 6-7，trace 覆盖七环。"""

    embed_fn: object  # Callable[[list[str]], list[list[float]]]
    llm: LLMClient | None = None
    raw_docs: list[RawDoc] = field(default_factory=lambda: RAW_DOCS)
    config: RagConfig = field(default_factory=RagConfig)

    def __post_init__(self) -> None:
        self.trace: list[RingTrace] = []
        children: list[Chunk] = []
        parents: list[Chunk] = []
        n_pages = n_chars_before = n_chars_after = n_sections = 0
        for raw in self.raw_docs:
            doc = parse(raw)
            n_pages += len(raw.pages)
            n_chars_before += len(doc.text)
            doc = clean(doc)
            n_chars_after += len(doc.text)
            cs, ps = chunk_structure(doc)
            children += cs
            parents += ps
            n_sections += len(ps)
            enrich(cs, doc)
        self.trace.append(
            RingTrace(
                ring=1, stage="parsing",
                summary=f"{len(self.raw_docs)} 篇 / {n_pages} 页 → {n_chars_before} 字符",
                data={"docs": len(self.raw_docs), "pages": n_pages, "chars": n_chars_before},
            )
        )
        self.trace.append(
            RingTrace(
                ring=2, stage="cleaning",
                summary=f"去页眉页脚/乱码/重复 → {n_chars_after} 字符",
                data={"chars_before": n_chars_before, "chars_after": n_chars_after},
            )
        )
        self.trace.append(
            RingTrace(
                ring=3, stage="chunking",
                summary=f"{n_sections} 节 → {len(children)} child 块（结构对齐+父子）",
                data={"children": len(children), "parents": len(parents), "sections": n_sections},
            )
        )
        accepted, rejected = metadata_gate(children)
        self.trace.append(
            RingTrace(
                ring=4, stage="metadata",
                summary=f"元数据门禁：{len(accepted)} 通过 / {len(rejected)} 拒绝入索引",
                data={"accepted": len(accepted), "rejected": len(rejected)},
            )
        )
        self.index = build_index(accepted, parents, self.embed_fn, self.config.corpus_version)
        reconcile(self.index, len(accepted), self.config.corpus_version)
        self.trace.append(
            RingTrace(
                ring=5, stage="indexing",
                summary=f"BM25 + 向量索引：{len(self.index.chunks)} 块，对账通过",
                data={"indexed": len(self.index.chunks), "version": self.index.version},
            )
        )

    def answer(self, query: str) -> RagResult:
        query_vec = self.embed_fn([query])[0]
        hits = retrieve(
            query, self.index, query_vec,
            top_k=self.config.top_k,
            alpha=self.config.alpha,
            bm25_saturation=self.config.bm25_saturation,
        )
        max_score = hits[0].score if hits else 0.0
        trace = list(self.trace) + [
            RingTrace(
                ring=6, stage="retrieval",
                summary=(
                    f"top_k={self.config.top_k} alpha={self.config.alpha} "
                    f"max_score={max_score:.3f}"
                ),
                data={
                    "max_score": round(max_score, 4),
                    "hits": [
                        {"chunk_id": h.chunk.chunk_id, "source": h.chunk.meta.source if h.chunk.meta else "?",
                         "score": round(h.score, 4)}
                        for h in hits[:3]
                    ],
                },
            )
        ]
        if not hits or max_score < self.config.refuse_threshold:
            answer = refuse(query, f"max hybrid score {max_score:.3f} < threshold {self.config.refuse_threshold}")
        else:
            answer = generate(query, hits, self.llm, max_tokens=self.config.max_tokens)  # type: ignore[arg-type]
        trace.append(
            RingTrace(
                ring=7, stage="generation",
                summary=(
                    f"refused={answer.refused}, citations={len(answer.citations)}"
                ),
                data={"refused": answer.refused, "citations": len(answer.citations)},
            )
        )
        return RagResult(answer=answer, trace=trace)

    def answer_with_frozen_hits(self, query: str, hits: list[Hit]) -> RagResult:
        """冻结检索（固定块）评测生成环——评测任何一环时 mock 掉相邻环。"""
        answer = generate(query, hits, self.llm, max_tokens=self.config.max_tokens)  # type: ignore[arg-type]
        trace = [RingTrace(ring=7, stage="generation", summary="frozen-retrieval eval",
                           data={"refused": answer.refused, "citations": len(answer.citations)})]
        return RagResult(answer=answer, trace=trace)


def rag_answer(query: str, embed_fn: object, llm: LLMClient, config: RagConfig | None = None) -> Answer:
    """章节骨架的同名入口：retrieve → refuse | render+generate。"""
    return RagPipeline(embed_fn=embed_fn, llm=llm, config=config or RagConfig()).answer(query).answer
