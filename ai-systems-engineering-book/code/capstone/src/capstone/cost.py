"""Ch60 capstone — cost: cost per task 记账（Ch40）。

按 token 用量 × tier 价格表估算。价格表为示例（本地部署直接电费成本近似 0，
云端价格用于路由决策演示）；口径稳定的是"每任务几次调用、多少 token"。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pydantic import BaseModel

# tier → (input_price, output_price)，单位：元 / 1k tokens（示例价格表）
PRICE_PER_1K: dict[str, tuple[float, float]] = {
    "premium": (0.060, 0.180),
    "standard": (0.004, 0.012),
    "economy": (0.001, 0.003),
}
DEFAULT_TIER = "economy"


class CostEntry(BaseModel):
    task_id: str
    ts: float
    tier: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: float


def estimate_cost(tier: str, prompt_tokens: int, completion_tokens: int) -> float:
    p_in, p_out = PRICE_PER_1K.get(tier, PRICE_PER_1K[DEFAULT_TIER])
    return round(prompt_tokens / 1000 * p_in + completion_tokens / 1000 * p_out, 6)


class CostLedger:
    """每次模型调用一条记录（tier/model/tokens/cost/task_id）——成本报表的地基。"""

    def __init__(self) -> None:
        self.entries: list[CostEntry] = []

    def record(
        self, task_id: str, tier: str, model: str,
        prompt_tokens: int, completion_tokens: int,
    ) -> CostEntry:
        entry = CostEntry(
            task_id=task_id,
            ts=time.time(),
            tier=tier,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=estimate_cost(tier, prompt_tokens, completion_tokens),
        )
        self.entries.append(entry)
        return entry

    def task_cost(self, task_id: str) -> dict:
        rows = [e for e in self.entries if e.task_id == task_id]
        return {
            "calls": len(rows),
            "prompt_tokens": sum(e.prompt_tokens for e in rows),
            "completion_tokens": sum(e.completion_tokens for e in rows),
            "cost": round(sum(e.cost for e in rows), 6),
            "tiers": sorted({e.tier for e in rows}),
        }

    def total(self) -> dict:
        return {
            "tasks": len({e.task_id for e in self.entries}),
            "calls": len(self.entries),
            "cost": round(sum(e.cost for e in self.entries), 6),
        }
