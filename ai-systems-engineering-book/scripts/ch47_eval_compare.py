"""Ch47 评测护航：同一评测集跨端点对比（FP16 基线 vs 量化模型，Ch45 纪律）

复用 ch07 的 prompt/schema 与判分（first-pass，无修复循环），但对任意
OpenAI-compatible 端点评测——本地 Ollama / vLLM FP16 / vLLM AWQ 用同一把尺。

用法：python3 ch47_eval_compare.py --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen2.5-7B-Instruct --dataset dataset.jsonl --tag fp16 \
  --out /root/autodl-tmp/ch47_eval_fp16.json
"""
import argparse
import json
import re
from datetime import datetime, timezone

import httpx

SCHEMA = (
    "输出一个 JSON 对象，字段如下：\n"
    '  "category": "refund" | "logistics" | "other"\n'
    '  "urgency": "low" | "medium" | "high"\n'
    '  "summary": "工单摘要，不超过20个汉字"\n'
    '  "needs_human": true | false\n'
    "只输出这个 JSON 对象，不要输出任何其他内容。"
)
SYSTEM = f"""你是工单结构化提取器。

[schema]
{SCHEMA}

[规则]
- 只输出一个 JSON 对象，不加围栏、不加解释。
- 字段值必须严格遵守 schema 的取值范围与类型。
"""
CATEGORIES = {"refund", "logistics", "other"}
URGENCIES = {"low", "medium", "high"}


def validate(text: str) -> tuple[bool, str]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return False, "no_json"
    try:
        j = json.loads(m.group(0))
    except json.JSONDecodeError:
        return False, "json_invalid"
    if j.get("category") not in CATEGORIES:
        return False, "category"
    if j.get("urgency") not in URGENCIES:
        return False, "urgency"
    s = str(j.get("summary", "")).strip()
    if not s or len(s) > 40:
        return False, "summary"
    if not isinstance(j.get("needs_human"), bool):
        return False, "needs_human"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--dataset", default="dataset.jsonl")
    ap.add_argument("--tag", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cases = [json.loads(l) for l in open(args.dataset, encoding="utf-8") if l.strip()]
    rows = []
    with httpx.Client(timeout=60) as client:
        for c in cases:
            r = client.post(f"{args.base_url}/chat/completions", json={
                "model": args.model,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"<ticket>\n{c['input']}\n</ticket>"},
                ],
                "max_tokens": 512,
                "temperature": 0.0,
            })
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            ok, reason = validate(text)
            val = json.loads(re.search(r"\{.*\}", text, re.S).group(0)) if ok else {}
            rows.append({
                "id": c["id"], "schema_ok": ok, "fail_reason": reason,
                "category_ok": ok and val["category"] == c["expected"]["category"],
                "needs_human_ok": ok and val["needs_human"] == c["expected"]["needs_human"],
            })

    n = len(rows)
    metrics = {
        "n": n,
        "schema_ok": sum(r["schema_ok"] for r in rows) / n,
        "category_accuracy": sum(r["category_ok"] for r in rows) / n,
        "needs_human_accuracy": sum(r["needs_human_ok"] for r in rows) / n,
        "failures": {},
    }
    for r in rows:
        if not r["schema_ok"]:
            metrics["failures"][r["fail_reason"]] = metrics["failures"].get(r["fail_reason"], 0) + 1
    out = {"meta": {"model": args.model, "base_url": args.base_url, "tag": args.tag,
                    "prompt": "repair-system-v1 (ch07, first-pass)",
                    "ts": datetime.now(timezone.utc).isoformat()},
           "metrics": metrics, "rows": rows}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"saved → {args.out}")


if __name__ == "__main__":
    main()
