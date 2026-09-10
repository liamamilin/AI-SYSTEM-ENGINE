"""Ring 7 — Generation: 注入纪律（编号+出处+框架声明）+ 引用输出 + 拒答。"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from .client import LLMClient
from .models import Chunk, ChunkMeta
from .retrieval import Hit

SYSTEM_PROMPT = (
    "你是客服知识库助手。以下参考片段来自知识库，可能与问题不完全匹配，仅作为参考。"
    "只依据片段回答问题，引用片段时标注编号如 [1]；"
    "片段中没有答案时，明确回答「知识库中未找到」，不要编造。"
)

REFUSAL_TEXT = "未找到可靠来源：知识库中没有与该问题足够相关的资料，为避免误导，此处不作回答。"

_CITE_RE = re.compile(r"\[(\d+)\]")


class Citation(BaseModel):
    n: int
    chunk_id: str
    source: str
    section: str


class Answer(BaseModel):
    query: str
    text: str
    refused: bool = False
    refused_reason: str | None = None
    citations: list[Citation] = Field(default_factory=list)


def render_context(hits: list[Hit]) -> str:
    """编号 + 出处 + 框架声明（Ch27 注入纪律的具体化）。"""
    blocks: list[str] = []
    for i, h in enumerate(hits, 1):
        m: ChunkMeta | None = h.chunk.meta
        source = m.source if m else "unknown"
        date = m.date if m else "unknown"
        section = h.chunk.section
        body = h.parent.text if h.parent else h.chunk.text  # 父子块：注入父块
        blocks.append(f"[{i}] 来源：{source} · 章节：{section} · 日期：{date}\n{body}")
    return "\n\n".join(blocks)


def refuse(query: str, reason: str) -> Answer:
    """拒答路径必须存在：「找不到就说找不到」是功能，不是缺陷。"""
    return Answer(query=query, text=REFUSAL_TEXT, refused=True, refused_reason=reason)


def parse_citations(text: str, hits: list[Hit]) -> list[Citation]:
    out: list[Citation] = []
    seen: set[int] = set()
    for n in (int(m) for m in _CITE_RE.findall(text)):
        if n in seen or not 1 <= n <= len(hits):
            continue
        seen.add(n)
        h = hits[n - 1]
        m = h.chunk.meta
        out.append(
            Citation(
                n=n,
                chunk_id=h.chunk.chunk_id,
                source=m.source if m else "unknown",
                section=h.chunk.section,
            )
        )
    return out


def generate(query: str, hits: list[Hit], llm: LLMClient, *, max_tokens: int = 512) -> Answer:
    context = render_context(hits)
    user = f"参考片段：\n\n{context}\n\n问题：{query}\n\n请依据片段回答，引用时标注 [n]。"
    completion = llm.complete(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
        temperature=0.0,
        max_tokens=max_tokens,
    )
    return Answer(
        query=query,
        text=completion.text.strip(),
        citations=parse_citations(completion.text, hits),
    )


def render_for_eval(hits: list[Hit]) -> str:
    """冻结检索做生成评测时使用的同源 context（管道原则：任何一环都可 mock）。"""
    return render_context(hits)


def chunk_text(chunk: Chunk) -> str:
    return chunk.text
