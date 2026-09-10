"""Ring 1 — Parsing: 原始文件 → 文本（保持阅读顺序）。"""

from __future__ import annotations

from dataclasses import dataclass

from .corpus import RawDoc


@dataclass
class ParsedDoc:
    doc_id: str
    source: str
    date: str
    version: int
    acl: str
    text: str


def parse(raw: RawDoc) -> ParsedDoc:
    """逐页拼接（模拟 PDF 阅读顺序）；真实系统这里替换为 PDF/OCR 解析器。"""
    text = "\n\n".join(raw.pages)
    return ParsedDoc(
        doc_id=raw.doc_id,
        source=raw.source,
        date=raw.date,
        version=raw.version,
        acl=raw.acl,
        text=text,
    )
