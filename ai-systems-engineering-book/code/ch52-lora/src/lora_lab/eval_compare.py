"""基础 vs LoRA 模型在同一评测集上对比（复用 ch07 评测集 + 简化 runner）。

简化版 runner（相对 ch07 的 repair loop）：
- 单次生成（temperature=0，无 repair 重试）——LoRA 对比关心的是"训练后一次性输出是否变好"；
- 判分：schema_ok（可解析为合法 JSON）/ category_ok / needs_human_ok；
- 聚合两套指标 + 差值（delta = lora - base），落盘 results/{ts}/。

模型接入采用依赖注入：generate_fn(prompt) -> str。
真实调用封装在 make_mlx_generator（懒导入 mlx_lm，便于 mock 测试）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = frozenset({"refund", "logistics", "other"})
SYSTEM_TEMPLATE = """你是工单结构化提取器。

[schema]
输出一个 JSON 对象，字段如下：
  "category": "refund" | "logistics" | "other"
  "urgency": "low" | "medium" | "high"
  "summary": "工单摘要，不超过20个汉字"
  "needs_human": true | false
只输出这个 JSON 对象，不要输出任何其他内容。
"""


def find_default_dataset() -> Path:
    """默认复用 ch07 的 30 条评测集（同仓库相对路径定位）。"""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "code" / "ch07-structured-output" / "evals" / "dataset.jsonl"
        if candidate.exists():
            return candidate
        if parent.name == "ch52-lora":
            candidate = parent.parent / "ch07-structured-output" / "evals" / "dataset.jsonl"
            if candidate.exists():
                return candidate
    raise FileNotFoundError(
        "default dataset (ch07 evals/dataset.jsonl) not found; pass --dataset explicitly"
    )


def load_dataset(path: str | Path) -> list[dict]:
    """ch07 评测集格式：{"id", "input", "expected": {"category", "needs_human"}}。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"eval dataset not found: {path}")
    cases: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"line {i + 1}: invalid JSON ({e})") from e
            for key in ("id", "input", "expected"):
                if key not in case:
                    raise ValueError(f"line {i + 1}: missing required field {key!r}")
            cases.append(case)
    if not cases:
        raise ValueError(f"{path}: empty dataset")
    return cases


def extract_json(text: str) -> dict | None:
    """从模型输出中提取第一个平衡的 JSON 对象（容忍围栏/前后缀）。"""
    text = text.strip()
    if "```" in text:
        text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    value = json.loads(candidate)
                except json.JSONDecodeError:
                    return None
                return value if isinstance(value, dict) else None
    return None


def judge_case(output_text: str, expected: dict) -> dict:
    """单条判分：schema_ok / category_ok / needs_human_ok。"""
    value = extract_json(output_text)
    row: dict = {"id": expected["id"], "schema_ok": value is not None}
    if value is None:
        row["category_ok"] = False
        row["needs_human_ok"] = False
        return row
    category = value.get("category")
    needs_human = value.get("needs_human")
    row["category_ok"] = isinstance(category, str) and category.strip().lower() in CATEGORIES and (
        category.strip().lower() == expected["expected"]["category"]
    )
    if isinstance(needs_human, bool):
        row["needs_human_ok"] = needs_human == expected["expected"]["needs_human"]
    else:
        row["needs_human_ok"] = False
    return row


def aggregate(rows: list[dict]) -> dict:
    """聚合一组判分结果。"""
    n = len(rows)
    if n == 0:
        raise ValueError("cannot aggregate over zero rows")
    return {
        "n": n,
        "schema_ok_rate": sum(r["schema_ok"] for r in rows) / n,
        "category_accuracy": sum(r["category_ok"] for r in rows) / n,
        "needs_human_accuracy": sum(r["needs_human_ok"] for r in rows) / n,
    }


def run_model(
    generate_fn: Callable[[str], str],
    cases: list[dict],
    *,
    max_cases: int = 0,
) -> tuple[list[dict], dict, float]:
    """在一个评测集上跑一个模型（generate_fn），返回 (逐条结果, 聚合指标, 用时秒)。"""
    import time

    system = SYSTEM_TEMPLATE
    rows: list[dict] = []
    t0 = time.perf_counter()
    for case in cases[: max_cases or None]:
        prompt = f"<ticket>\n{case['input']}\n</ticket>"
        output = generate_fn(prompt)
        row = judge_case(output, case)
        row["output"] = output
        rows.append(row)
    elapsed = time.perf_counter() - t0
    return rows, aggregate(rows), elapsed


def diff_metrics(base: dict, lora: dict) -> dict:
    """delta = lora - base（三个核心指标）。"""
    return {
        key: round(lora[key] - base[key], 4)
        for key in ("schema_ok_rate", "category_accuracy", "needs_human_accuracy")
    }


def write_results(out_dir: Path, *, base_rows, lora_rows, base_metrics, lora_metrics,
                  metadata: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for name, rows in (("base", base_rows), ("lora", lora_rows)):
            for r in rows:
                f.write(json.dumps({"model": name, **r}, ensure_ascii=False) + "\n")
    payload = {
        **metadata,
        "base": base_metrics,
        "lora": lora_metrics,
        "delta": diff_metrics(base_metrics, lora_metrics),
    }
    with open(out_dir / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_dir


def resolve_adapter_dir(adapter: str) -> str:
    """mlx_lm.load 的 adapter_path 语义是目录（含 adapter_config.json + adapters.safetensors）。

    兼容两种写法：目录直接用；传 *.safetensors 快照文件则取其父目录（mlx-lm 0.31 实测语义）。
    """
    p = Path(adapter)
    if p.suffix == ".safetensors":
        return str(p.parent)
    return adapter


def make_mlx_generator(model: str, adapter: str | None = None, max_tokens: int = 256):
    """真实 MLX 推理封装：temperature=0 单次生成（懒导入，测试不触发）。"""
    try:
        from mlx_lm import generate as mlx_generate
        from mlx_lm import load as mlx_load
    except ImportError as e:  # pragma: no cover - 环境缺依赖时显式报错
        raise RuntimeError(
            "mlx_lm is required for real inference; install into .venv (see README)"
        ) from e

    if adapter:
        model_obj, tokenizer = mlx_load(model, adapter_path=resolve_adapter_dir(adapter))
    else:
        model_obj, tokenizer = mlx_load(model)

    def generate_fn(prompt: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_TEMPLATE},
            {"role": "user", "content": prompt},
        ]
        return str(
            mlx_generate(
                model_obj,
                tokenizer,
                prompt=tokenizer.apply_chat_template(messages, add_generation_prompt=True),
                max_tokens=max_tokens,
                verbose=False,
            )
        )

    return generate_fn


def main() -> None:
    ap = argparse.ArgumentParser(description="base vs LoRA eval comparison (ch07 dataset)")
    ap.add_argument("--base-model", required=True, help="base model path or HF repo id")
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir (mlx_lm lora output)")
    ap.add_argument("--dataset", default=None, help="default: ch07 evals/dataset.jsonl")
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--limit", type=int, default=0, help="limit cases (quick smoke)")
    ap.add_argument("--results-dir", default=None, help="default: results/ under this project")
    args = ap.parse_args()

    dataset = args.dataset or str(find_default_dataset())
    cases = load_dataset(dataset)
    print(f"dataset: {dataset} ({len(cases)} cases)")

    base_gen = make_mlx_generator(args.base_model, max_tokens=args.max_tokens)
    base_rows, base_metrics, base_sec = run_model(base_gen, cases, max_cases=args.limit)
    print(f"base done in {base_sec:.1f}s: {base_metrics}")

    if args.adapter:
        lora_gen = make_mlx_generator(args.base_model, adapter=args.adapter, max_tokens=args.max_tokens)
        lora_rows, lora_metrics, lora_sec = run_model(lora_gen, cases, max_cases=args.limit)
        print(f"lora done in {lora_sec:.1f}s: {lora_metrics}")
    else:
        lora_rows, lora_metrics = [], {"note": "no adapter given; base-only run"}

    results_root = Path(args.results_dir) if args.results_dir else Path(__file__).resolve().parents[2] / "results"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = write_results(
        results_root / ts,
        base_rows=base_rows,
        lora_rows=lora_rows,
        base_metrics=base_metrics,
        lora_metrics=lora_metrics,
        metadata={
            "chapter": "ch52-lora",
            "base_model": args.base_model,
            "adapter": args.adapter,
            "dataset": dataset,
            "max_tokens": args.max_tokens,
            "date": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(f"results -> {out_dir}")


if __name__ == "__main__":
    main()
