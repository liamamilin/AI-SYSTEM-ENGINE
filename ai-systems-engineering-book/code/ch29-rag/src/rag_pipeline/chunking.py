"""Ring 3 — Chunking: 结构对齐分块（按章节标题）+ 父子块。

child 块用于检索（小块准），parent 块用于生成注入（上下文完整）——
修复"块小了检得准但读不懂、块大了读得懂但检不准"的两难。
"""

from __future__ import annotations

from .models import Chunk
from .parsing import ParsedDoc


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    title, lines, started = "概览", [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if started and any(l.strip() for l in lines):
                sections.append((title, "\n".join(lines).strip()))
            title, lines, started = line[3:].strip(), [], True
        else:
            lines.append(line)
    if started and any(l.strip() for l in lines):
        sections.append((title, "\n".join(lines).strip()))
    return sections


def chunk_structure(doc: ParsedDoc) -> tuple[list[Chunk], list[Chunk]]:
    """返回 (children, parents)：child 按段落切，parent 为整节文本。"""
    children: list[Chunk] = []
    parents: list[Chunk] = []
    for si, (title, section_text) in enumerate(_split_sections(doc.text)):
        parent_id = f"{doc.doc_id}:sec{si}"
        parents.append(
            Chunk(
                chunk_id=parent_id,
                doc_id=doc.doc_id,
                kind="parent",
                text=section_text,
                section=title,
            )
        )
        for pi, para in enumerate(p for p in section_text.split("\n\n") if p.strip()):
            children.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}:sec{si}p{pi}",
                    doc_id=doc.doc_id,
                    kind="child",
                    text=para.strip(),
                    section=title,
                    parent_id=parent_id,
                )
            )
    return children, parents
