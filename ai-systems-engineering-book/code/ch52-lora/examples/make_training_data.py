"""生成冒烟训练数据：工单结构化分类任务（与 ch07 评测集同分布、措辞不同）。

设计（对齐 ch50/ch51/ch52 正文）：
- task 条目：教"工单 -> 指定 JSON 格式"的目标行为（assistant 回复 = 符合 schema 的 JSON）；
- general 条目：通用问答混入（配比检查演示，防止灾难性遗忘）；
- 生成是确定性的（固定词库 + 固定顺序），不采样 ch07 评测集原文——训练/评测不交叉。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lora_lab.data_prep import prepare, write_jsonl  # noqa: E402

SYSTEM = "你是工单结构化提取器。只输出一个 JSON 对象：{\"category\": \"refund\"|\"logistics\"|\"other\", \"urgency\": \"low\"|\"medium\"|\"high\", \"summary\": \"...\", \"needs_human\": true|false}。"

# 退款类措辞（避开 ch07 评测集原文）
REFUND = [
    "蓝牙耳机连不上还杂音，退了",
    "沙发面料掉色严重，要求退款",
    "水杯保温效果差，我要退钱",
    "手机壳用一周就裂了，退货",
    "买的台灯不亮，退款处理",
    "鞋子开线了，给我退款",
    "充电器发热严重不敢用，退货",
    "口红颜色和图片差太多，退款",
    "儿童玩具缺零件，要求退款",
    "保温饭盒漏水，退了吧",
]
LOGISTICS = [
    "快递五天了还在揽收状态",
    "物流显示派送但没收到货",
    "包裹卡在转运中心三天了",
    "订单发货十天了还没到",
    "快递员说放驿站但驿站没找到",
]
OTHER = [
    "会员优惠券怎么领取",
    "怎么修改收货地址",
    "这个型号有没有白色",
]
GENERAL = [
    "请用一句话解释什么是机器学习。",
    "把这句话翻译成英文：今天天气很好。",
    "写一句鼓励学习的话。",
    "1加1等于几？",
]


def assistant_json(category: str, urgency: str, summary: str, needs_human: bool) -> str:
    return json.dumps(
        {"category": category, "urgency": urgency, "summary": summary, "needs_human": needs_human},
        ensure_ascii=False,
    )


def task_record(user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "kind": "task",
    }


def general_record(user: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": "好的，我来帮你解答。"},
        ],
        "kind": "general",
    }


def main(out_dir: str = "data", per_bucket_repeat: int = 2) -> None:
    records: list[dict] = []
    for i in range(per_bucket_repeat):
        for text in REFUND:
            records.append(task_record(text, assistant_json("refund", "low", text[:12], False)))
        for text in LOGISTICS:
            records.append(task_record(text, assistant_json("logistics", "medium", text[:12], False)))
        for text in OTHER:
            records.append(task_record(text, assistant_json("other", "low", text[:12], False)))
        for text in GENERAL:
            records.append(general_record(text))
    raw = Path(out_dir) / "raw.jsonl"
    write_jsonl(records, raw)
    summary = prepare(
        raw,
        Path(out_dir),
        val_ratio=0.1,
        seed=42,
        min_general_ratio=0.1,  # Ch50 配比门禁：general 至少 10%
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    args = sys.argv[1:] or ["2"]
    main(out_dir=args[1] if len(args) > 1 else "data",
         per_bucket_repeat=int(args[0]))
