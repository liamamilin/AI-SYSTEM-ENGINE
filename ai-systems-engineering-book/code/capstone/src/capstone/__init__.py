"""Ch60 capstone：生产级 AI Agent 平台骨架（任务 A：内部知识助手）。

组装：ch11 网关 + ch08/19 Agent Loop（加审批位）+ ch29 七环 RAG（语料换域）
+ ch33 Job 化/降级 + ch59 密级贯穿 + ch36/40 审计与成本。
"""

from .audit import AuditLog, AuditRecord
from .cost import CostLedger, estimate_cost
from .platform import CAPSTONE_ACL, CAPSTONE_DOCS, KnowledgePlatform, TaskOutcome, toy_embed_fn
from .security import AccessRule, CapabilityTable, UserContext, acl_filter
from .tools import ApprovalGate, ApprovalRequiredError, ToolHost

__all__ = [
    "AuditLog", "AuditRecord", "CostLedger", "estimate_cost",
    "KnowledgePlatform", "TaskOutcome", "CAPSTONE_DOCS", "CAPSTONE_ACL",
    "AccessRule", "CapabilityTable", "UserContext", "acl_filter",
    "ApprovalGate", "ApprovalRequiredError", "ToolHost", "toy_embed_fn",
]
