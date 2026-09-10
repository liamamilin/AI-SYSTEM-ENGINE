"""Ch60 capstone — audit: 审计链（Ch36 trace 对齐 + Ch59 审计五要素）。

完整记录：谁（user）+ 何时（ts）+ 问了什么（哈希，脱敏存储）+ 检索到什么
（允许/被拒块 ID——被拒记录是越权尝试的审计信号）+ 调用了什么工具 + 审批了什么。
审计随任务产生（不是事后补写）；写路径任务的审计必须完整（require_complete
门禁，字段缺失拒绝出平台——审计完整率是自动化门禁）。
"""

from __future__ import annotations

import json
from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    """一次任务的一条完整审计记录。"""

    task_id: str
    ts: str
    user_id: str
    question_hash: str  # 问题存哈希不存原文（脱敏存储，ch59）
    question_chars: int = 0
    retrieved_doc_ids: list[str] = Field(default_factory=list)  # 允许进 context 的块
    denied_doc_ids: list[str] = Field(default_factory=list)     # 被拒（含越权尝试）
    clearance_touched: str = "none"                             # 本次接触的最高密级
    tool_calls: list[dict] = Field(default_factory=list)
    approvals: list[dict] = Field(default_factory=list)
    answer_id: str | None = None
    refused: bool = False
    degraded: bool = False
    stop: str = ""
    cost: float = 0.0
    cost_calls: int = 0

    def require_complete(self, *, strict: bool = True) -> None:
        """审计完整率门禁：核心字段一律必填；strict（写路径）时链路字段全非空。"""
        missing = [
            k for k in ("task_id", "ts", "user_id", "question_hash", "answer_id")
            if not getattr(self, k)
        ]
        if strict:
            for k in ("tool_calls", "approvals", "stop"):
                if not getattr(self, k):
                    missing.append(k)
            if self.cost <= 0:
                missing.append("cost")
        if missing:
            raise ValueError(f"审计记录不完整，缺失字段: {missing}（task {self.task_id}）")

    def replay(self) -> str:
        """一次任务的审计链可完整回放（Ch36 trace 回放的审计版）。"""
        lines = [
            f"[audit] task={self.task_id} ts={self.ts}",
            f"  谁: {self.user_id}  问什么: sha:{self.question_hash} ({self.question_chars} chars)",
            f"  检索: 允许={self.retrieved_doc_ids} 拒绝={self.denied_doc_ids} 密级={self.clearance_touched}",
        ]
        for tc in self.tool_calls:
            lines.append(f"  工具: {tc.get('tool')} ok={tc.get('ok')}")
        for ap in self.approvals:
            lines.append(f"  审批: request={ap.get('request_id')} by={ap.get('approver')} decision={ap.get('decision')}")
        lines.append(
            f"  结果: answer={self.answer_id} refused={self.refused} "
            f"degraded={self.degraded} stop={self.stop} cost={self.cost}"
        )
        return "\n".join(lines)


class AuditLog:
    """追加式审计日志（进程内形态；生产版落 append-only 存储，语义不变）。"""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> AuditRecord:
        self.records.append(record)
        return record

    def get(self, task_id: str) -> AuditRecord | None:
        return next((r for r in self.records if r.task_id == task_id), None)

    def write(self, path: str) -> int:
        with open(path, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r.model_dump(), ensure_ascii=False) + "\n")
        return len(self.records)
