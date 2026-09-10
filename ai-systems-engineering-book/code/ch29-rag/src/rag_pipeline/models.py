"""Shared models for the seven-ring pipeline (Ch29)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChunkMeta(BaseModel):
    """Ring 4 (Metadata): 溯源与过滤的地基——没有元数据的块不允许入索引。"""

    source: str
    section: str
    date: str
    version: int = 1
    acl: str = "internal"


class Chunk(BaseModel):
    """检索单元（child）或注入单元（parent，父子块模式）。"""

    chunk_id: str
    doc_id: str
    kind: str = "child"  # "child" | "parent"
    text: str
    section: str = "概览"
    parent_id: str | None = None
    meta: ChunkMeta | None = None


class RingTrace(BaseModel):
    """一环的输入输出快照——分层归因（"答错了"定位到环）的依据。"""

    ring: int
    stage: str  # parsing|cleaning|chunking|metadata|indexing|retrieval|generation
    summary: str
    data: dict[str, object] = Field(default_factory=dict)
