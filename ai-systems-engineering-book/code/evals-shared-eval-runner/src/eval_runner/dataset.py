"""Dataset loading with version stamping (Ch13 format)."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass


@dataclass
class Case:
    id: str
    input: str
    expected: dict
    metadata: dict


def load_dataset(path: str) -> tuple[list[Case], dict]:
    """Returns (cases, dataset_info{id, sha256, n}). Fails loudly on bad lines."""
    cases = []
    for i, line in enumerate(open(path, encoding="utf-8")):
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)  # bad JSON -> crash (fail loudly, Ch13 rule)
        for k in ("id", "input", "expected"):
            if k not in raw:
                raise ValueError(f"{path}:{i + 1} missing field {k!r}")
        cases.append(Case(id=raw["id"], input=raw["input"], expected=raw["expected"],
                          metadata=raw.get("metadata", {})))
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]
    return cases, {"path": os.path.basename(path), "n": len(cases), "sha256_12": sha}
