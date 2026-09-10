"""Ch33 component: 降级矩阵（Ch35 预设计矩阵在本章的最小落点）.

矩阵（Ch35 正文，模型相关两行）：
  模型 API 故障     → 回退链（第 11 章）→ degraded 标记可见
  回退链全部耗尽    → 排队/稍后通知（同步请求转 Job）—— 绝不假装成功
设计纪律：降级是预先设计的、必须可见的（degraded 标记 + 事件）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DegradationRow:
    fault: str            # 故障形态
    mode: str             # 降级形态
    user_visible: str     # 用户可见性（矩阵的第三列）


class DegradationMatrix:
    def __init__(self, rows: list[DegradationRow] | None = None):
        self.rows = rows or [
            DegradationRow("model_api_down", "fallback_chain", "回答带 degraded 标记"),
            DegradationRow("model_chain_exhausted", "queue_later", "明示降级：已转后台任务，稍后可查"),
        ]

    def row_for(self, fault: str) -> DegradationRow | None:
        return next((r for r in self.rows if r.fault == fault), None)

    def on_sync_total_failure(self) -> DegradationRow:
        """回退链耗尽时同步请求的唯一预案：排队/稍后通知（不抛 500 给用户裸错误）."""
        row = self.row_for("model_chain_exhausted")
        assert row is not None, "degradation matrix must pre-define chain-exhausted row"
        return row
