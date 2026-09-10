"""训练数据准备：chat 格式 JSONL 校验（schema、配比检查、train/val 切分）。

数据格式（Ch51 定义）：{"messages": [{"role": "system"|"user"|"assistant", "content": "..."}, ...]}
可选顶层字段 "kind"："task"（目标任务，默认）| "general"（通用保持数据）——Ch50 配比检查用。

产线约定：
- 只有 assistant 段参与 loss（掩码语义），所以最后一条消息必须是 assistant；
- train/val 切分必须确定性（固定 seed），避免"每次训练数据集不同"（Ch17 可复现纪律）；
- 配比检查是门禁：general 占比低于下限时拒绝开始训练（Ch50）。
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

VALID_ROLES = ("system", "user", "assistant")
VALID_KINDS = ("task", "general")


class DataFormatError(ValueError):
    """训练数据不符合 chat JSONL 契约。"""


def validate_record(record: object, index: int = 0) -> dict:
    """校验单条 chat 记录，返回规范化后的记录。失败抛 DataFormatError。"""
    if not isinstance(record, dict):
        raise DataFormatError(f"line {index + 1}: record must be a JSON object")
    if "messages" not in record:
        raise DataFormatError(f"line {index + 1}: missing required field 'messages'")
    messages = record["messages"]
    if not isinstance(messages, list) or not messages:
        raise DataFormatError(f"line {index + 1}: 'messages' must be a non-empty list")

    normalized = {k: v for k, v in record.items() if k != "messages"}
    seen_user = False
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            raise DataFormatError(f"line {index + 1}: message {i} must be an object")
        role = msg.get("role")
        content = msg.get("content")
        if role not in VALID_ROLES:
            raise DataFormatError(
                f"line {index + 1}: message {i} invalid role {role!r}, must be one of {VALID_ROLES}"
            )
        if not isinstance(content, str) or not content.strip():
            raise DataFormatError(f"line {index + 1}: message {i} content must be a non-empty string")
        if role == "user":
            seen_user = True
        if role == "assistant" and not seen_user:
            raise DataFormatError(
                f"line {index + 1}: message {i} assistant before any user (target needs a prompt)"
            )
    last_role = messages[-1]["role"]
    if last_role != "assistant":
        raise DataFormatError(
            f"line {index + 1}: last message role is {last_role!r}; "
            "SFT target is the assistant segment, so it must be last"
        )

    kind = normalized.get("kind", "task")
    if kind not in VALID_KINDS:
        raise DataFormatError(f"line {index + 1}: 'kind' must be one of {VALID_KINDS}, got {kind!r}")
    normalized["kind"] = kind
    normalized["messages"] = messages
    return normalized


def load_records(path: str | Path) -> list[dict]:
    """读取 chat 格式 JSONL 并逐条校验。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")
    records: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                raise DataFormatError(f"line {i + 1}: invalid JSON ({e})") from e
            records.append(validate_record(raw, index=i))
    if not records:
        raise DataFormatError(f"{path}: no valid records")
    return records


def mix_ratio(records: list[dict]) -> dict:
    """统计 task/general 配比（Ch50：配比是数据门禁的一部分）。"""
    counts = Counter(r.get("kind", "task") for r in records)
    total = sum(counts.values())
    return {
        "task": counts.get("task", 0),
        "general": counts.get("general", 0),
        "general_ratio": counts.get("general", 0) / total,
    }


def check_mix_ratio(records: list[dict], min_general_ratio: float = 0.0) -> None:
    """general 占比低于下限时拒绝（返回 None 表示通过，否则抛错）。"""
    stats = mix_ratio(records)
    if stats["general_ratio"] < min_general_ratio:
        raise DataFormatError(
            f"mix ratio gate failed: general ratio {stats['general_ratio']:.2f} "
            f"< required {min_general_ratio:.2f} (task={stats['task']}, general={stats['general']})"
        )


def split_records(
    records: list[dict], val_ratio: float = 0.1, seed: int = 42
) -> tuple[list[dict], list[dict]]:
    """确定性 train/val 切分（固定 seed；同一数据两次切分结果必须一致）。"""
    if not 0.0 <= val_ratio < 1.0:
        raise ValueError(f"val_ratio must be in [0, 1), got {val_ratio}")
    if not records:
        raise ValueError("cannot split an empty dataset")
    order = list(range(len(records)))
    rng = random.Random(seed)
    rng.shuffle(order)
    n_val = max(1, round(len(records) * val_ratio)) if val_ratio > 0 else 0
    # 训练集不能为空：数据极少时宁可 val 为空，也保住 train（否则没有可学习样本）
    n_val = min(n_val, len(records) - 1)
    val_idx = set(order[:n_val])
    train = [r for i, r in enumerate(records) if i not in val_idx]
    val = [r for i, r in enumerate(records) if i in val_idx]
    return train, val


def write_jsonl(records: list[dict], path: str | Path) -> int:
    """写 JSONL（每行一条 JSON），返回条数。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def prepare(
    source: str | Path,
    out_dir: str | Path,
    *,
    val_ratio: float = 0.1,
    seed: int = 42,
    min_general_ratio: float = 0.0,
) -> dict:
    """端到端：加载 -> 配比门禁 -> 切分 -> 落盘 train.jsonl / valid.jsonl。返回摘要。

    输出文件名用 mlx-lm lora 的目录约定（--data 接收目录，读 train.jsonl/valid.jsonl）。
    """
    records = load_records(source)
    check_mix_ratio(records, min_general_ratio=min_general_ratio)
    train, val = split_records(records, val_ratio=val_ratio, seed=seed)
    out_dir = Path(out_dir)
    n_train = write_jsonl(train, out_dir / "train.jsonl")
    n_val = write_jsonl(val, out_dir / "valid.jsonl")
    return {
        "source": str(source),
        "out_dir": str(out_dir),
        "train": n_train,
        "val": n_val,
        "mix": mix_ratio(records),
        "val_ratio": val_ratio,
        "seed": seed,
    }
