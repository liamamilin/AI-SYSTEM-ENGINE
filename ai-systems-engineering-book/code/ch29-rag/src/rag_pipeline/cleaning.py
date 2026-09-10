"""Ring 2 — Cleaning: 去页眉页脚/乱码/重复。"""

from __future__ import annotations

import re

from .parsing import ParsedDoc

_HEADER_RE = re.compile(r"^【.*】$")
_FOOTER_RE = re.compile(r"^第 \d+ 页 / 共 \d+ 页")
_MOJIBAKE_RE = re.compile(r"\ufffd+")


def clean(doc: ParsedDoc) -> ParsedDoc:
    kept: list[str] = []
    seen: set[str] = set()
    for line in doc.text.splitlines():
        line = _MOJIBAKE_RE.sub("", line)
        if _HEADER_RE.match(line.strip()) or _FOOTER_RE.match(line.strip()):
            continue
        if line.strip() and line.strip() in seen:  # 去重复行
            continue
        seen.add(line.strip())
        kept.append(line)
    doc.text = "\n".join(kept).strip()
    return doc
