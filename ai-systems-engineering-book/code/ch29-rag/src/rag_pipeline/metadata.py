"""Ring 4 — Metadata: 来源/章节/日期/版本/权限 + 入索引前的完整率门禁。"""

from __future__ import annotations

from .models import Chunk, ChunkMeta
from .parsing import ParsedDoc


def enrich(children: list[Chunk], doc: ParsedDoc) -> list[Chunk]:
    for c in children:
        c.meta = ChunkMeta(
            source=doc.source,
            section=c.section,
            date=doc.date,
            version=doc.version,
            acl=doc.acl,
        )
    return children


def metadata_gate(chunks: list[Chunk]) -> tuple[list[Chunk], list[Chunk]]:
    """缺 source/date 的块不允许入索引（元数据完整率 = 自动化门禁）。"""
    accepted = [
        c for c in chunks
        if c.meta is not None and c.meta.source.strip() and c.meta.date.strip()
    ]
    rejected = [c for c in chunks if c not in accepted]
    return accepted, rejected
