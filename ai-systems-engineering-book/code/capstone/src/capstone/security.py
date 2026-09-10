"""Ch60 capstone — security: 能力约束表 + ACL 检索过滤（ch59 Minimal Implementation 吸收版）。

红线（Ch59）：权限必须是检索的前置条件——context 不可撤回，所以过滤在检索层做，
不在生成层做。fail-closed：无 ACL 的块宁可检索不到（默认拒绝）。
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

CLEARANCE_LEVELS: dict[str, int] = {"public": 0, "internal": 1, "confidential": 2}


class AccessRule(BaseModel):
    """块的 ACL 元数据——没有完整 ACL 的文档拒绝入索引（入库门禁，ch59）。"""

    doc_id: str
    clearance: str  # public / internal / confidential
    departments: set[str] = set()  # 可访问部门（public 时空集即可）

    @field_validator("clearance")
    @classmethod
    def acl_complete(cls, v: str) -> str:
        if v not in CLEARANCE_LEVELS:
            raise ValueError(f"未知密级 {v!r}：无 ACL 的块拒绝入索引")
        return v

    @property
    def level(self) -> int:
        return CLEARANCE_LEVELS[self.clearance]


class UserContext(BaseModel):
    user_id: str
    clearance: str
    departments: set[str]
    role: str = "employee"  # employee / it / approver（能力约束的角色位）

    @field_validator("clearance")
    @classmethod
    def known_clearance(cls, v: str) -> str:
        if v not in CLEARANCE_LEVELS:
            raise ValueError(f"未知用户密级 {v!r}")
        return v

    @property
    def level(self) -> int:
        return CLEARANCE_LEVELS[self.clearance]

    def can_access(self, rule: AccessRule) -> bool:
        """越权判定：密级不够或部门不符一律拒绝（默认拒绝，非白名单例外，ch59）。"""
        if self.level < rule.level:
            return False
        if rule.clearance == "public":
            return True
        return bool(self.departments & rule.departments)


def acl_filter(hits: list, user: UserContext, rules: dict[str, AccessRule]) -> tuple[list, list[str]]:
    """检索层 ACL 过滤（ch59 红线落点）：块通过 ACL 才进 context。

    返回 (allowed_hits, denied_doc_ids)——被拒的全量记录：
    越权访问尝试本身就是审计信号（Ch36）。
    fail-closed：规则缺失（rule is None）= 拒绝。
    """
    allowed, denied = [], []
    for hit in hits:
        rule = rules.get(hit.chunk.doc_id)
        if rule is None or not user.can_access(rule):
            denied.append(hit.chunk.doc_id)
            continue
        allowed.append(hit)
    return allowed, denied


class PermissionError_(PermissionError):
    """能力约束拒绝（区别于内置 PermissionError 语义噪声，显式类型便于测试）。"""


class CapabilityTable:
    """能力约束表（Ch38）：角色 × 工具白名单 + 写操作 L1 审批位（Ch25 分级）。"""

    READ_TOOLS = {"search_docs", "query_db"}
    WRITE_TOOLS = {"submit_request"}  # 写操作 → 必须 L1 审批（Ch60 红线）

    ROLE_TOOLS: dict[str, set[str]] = {
        "employee": READ_TOOLS | WRITE_TOOLS,
        "it": READ_TOOLS | WRITE_TOOLS,
        "approver": READ_TOOLS | WRITE_TOOLS,
        "guest": READ_TOOLS,  # guest 无写权限
    }

    def check(self, user: UserContext, tool: str) -> None:
        allowed = self.ROLE_TOOLS.get(user.role, set())
        if tool not in allowed:
            raise PermissionError_(f"角色 {user.role!r} 无工具权限: {tool}（默认拒绝）")
