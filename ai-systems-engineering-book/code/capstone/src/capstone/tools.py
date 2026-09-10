"""Ch60 capstone — tools: 3 个工具（形态参考 ch57 patch 工具链）+ L1 审批门（Ch25）。

- search_docs    ：只读，复用 ch29 检索 + security.acl_filter（检索层 ACL）
- query_db       ：只读 mock（仅 SELECT，on-behalf-of 语义：工具不持有自己的权限）
- submit_request ：写操作 → 唯一通道是 ApprovalGate 提交挂起请求；
                   写副作用只存在于 approve 路径——未经 L1 审批绝不执行（Ch60 红线）。

红线是结构性的，不是纪律性的：模型/工具代码里根本不存在"直接执行写操作"的路径。
"""

from __future__ import annotations

import hashlib
import json
import time
from pydantic import BaseModel, Field

from tool_calling.registry import ToolRegistry

from .security import CapabilityTable, PermissionError_, UserContext


class ApprovalRequiredError(PermissionError):
    """写操作未经 L1 审批就请求执行——必须失败，绝不静默放行。"""


class PendingRequest(BaseModel):
    request_id: str
    user_id: str
    req_type: str
    payload: str
    status: str = "pending"  # pending | executed | rejected
    created_ts: float = Field(default_factory=time.time)
    decided_by: str | None = None
    decided_ts: float | None = None
    effect: dict = Field(default_factory=dict)


class ApprovalGate:
    """L1 审批门：写操作的两阶段执行（提议 → 人工批准 → 落副作用）。

    幂等提交：同一 (user, type, payload) 返回同一 request_id（客户端/模型重试安全）。
    审批决定记录成审计事件（谁批了什么，Ch25 + Ch59）。
    """

    def __init__(self, executor, decisions_sink: list[dict] | None = None):
        self._executor = executor          # Callable[[PendingRequest], dict]（唯一写副作用入口）
        self._pending: dict[str, PendingRequest] = {}
        self.decisions: list[dict] = decisions_sink if decisions_sink is not None else []

    def submit(self, user_id: str, req_type: str, payload: str) -> PendingRequest:
        rid = hashlib.sha256(f"{user_id}|{req_type}|{payload}".encode()).hexdigest()[:12]
        if rid in self._pending and self._pending[rid].status == "pending":
            return self._pending[rid]
        req = PendingRequest(request_id=rid, user_id=user_id, req_type=req_type, payload=payload)
        self._pending[rid] = req
        return req

    def raise_if_not_approved(self, request_id: str) -> None:
        """显式拒绝路径：未经审批的写请求执行 → ApprovalRequiredError。"""
        req = self._pending.get(request_id)
        if req is None:
            raise ApprovalRequiredError(f"请求不存在: {request_id}")
        if req.status != "executed":
            raise ApprovalRequiredError(
                f"L1 审批未通过：写操作 {req.req_type}({request_id}) 拒绝执行（红线：未经审批绝不执行）"
            )

    def decide(self, request_id: str, approver: str, *, approve: bool) -> dict:
        """审批决定。approve=True 才触达 executor（写副作用唯一入口）。"""
        req = self._pending.get(request_id)
        if req is None:
            raise KeyError(f"请求不存在: {request_id}")
        if req.status != "pending":
            raise ValueError(f"请求 {request_id} 已终态: {req.status}")
        if not approve:
            req.status = "rejected"
            req.decided_by, req.decided_ts = approver, time.time()
            self.decisions.append({"request_id": req.request_id, "approver": approver, "decision": "rejected"})
            return {"request_id": req.request_id, "status": "rejected"}
        req.status = "executed"
        req.decided_by, req.decided_ts = approver, time.time()
        req.effect = self._executor(req)  # ← 写副作用只在这里发生
        self.decisions.append({"request_id": req.request_id, "approver": approver, "decision": "approved"})
        return {"request_id": req.request_id, "status": "executed", "effect": req.effect}

    def pending_ids(self) -> list[str]:
        return [r.request_id for r in self._pending.values() if r.status == "pending"]

    def get(self, request_id: str) -> PendingRequest | None:
        return self._pending.get(request_id)


class ToolHost:
    """把 3 个工具绑定到（platform × 用户）上的宿主：能力约束在 handler 入口检查。"""

    def __init__(self, platform, user: UserContext, table: CapabilityTable | None = None):
        self.platform = platform
        self.user = user
        self.table = table or CapabilityTable()
        self.used_docs: list[str] = []     # search_docs 允许的块（进 audit）
        self.denied_docs: list[str] = []   # 被拒块（越权尝试，进 audit）
        self.submitted: list[str] = []     # submit_request 挂起的 request_id

    # ---- 工具 1：search_docs（只读，复用 ch29 检索 + ACL 过滤） ----
    def search_docs(self, query: str) -> str:
        self.table.check(self.user, "search_docs")
        out = self.platform.search(self.user, query)
        self.used_docs.extend(d for d in out.allowed_ids if d not in self.used_docs)
        self.denied_docs.extend(d for d in out.denied_ids if d not in self.denied_docs)
        if not out.snippets:
            return json.dumps({"hits": 0, "denied": out.denied_ids, "note": "无可用来源（可能被权限过滤）"}, ensure_ascii=False)
        return json.dumps({"hits": len(out.snippets), "snippets": out.snippets}, ensure_ascii=False)

    # ---- 工具 2：query_db（只读 mock；SELECT-only，注入面收口） ----
    def query_db(self, sql: str) -> str:
        self.table.check(self.user, "query_db")
        s = sql.strip().rstrip(";").strip()
        if not s.upper().startswith(("SELECT", "WITH")):
            raise PermissionError_("query_db 是只读工具：仅允许 SELECT 查询")
        if ";" in s:
            raise PermissionError_("拒绝多语句 SQL")
        rows = self.platform.query_db(s)
        return json.dumps({"rows": rows, "n": len(rows)}, ensure_ascii=False)

    # ---- 工具 3：submit_request（写 → L1 审批；只提交，不执行） ----
    def submit_request(self, req_type: str, payload: str) -> str:
        self.table.check(self.user, "submit_request")
        req = self.platform.gate.submit(self.user.user_id, req_type, payload)
        self.submitted.append(req.request_id)
        return json.dumps(
            {
                "request_id": req.request_id,
                "status": "pending_approval",
                "note": "已提交 IT 审批队列，等待 L1 审批人批准后才会执行；请告知用户审批进度可后续查询。",
            },
            ensure_ascii=False,
        )

    # ---- 注册表（ch08 registry：模型只提议，宿主校验执行） ----
    def build_registry(self) -> ToolRegistry:
        reg = ToolRegistry()
        reg.register(
            self.search_docs,
            name="search_docs",
            description="搜索内部知识库（只读，带权限过滤）。返回编号片段与出处。",
            schema={"query": {"type": "string", "required": True, "description": "检索词"}},
        )
        reg.register(
            self.query_db,
            name="query_db",
            description="查询工单/资产数据库（只读，仅 SELECT）。",
            schema={"sql": {"type": "string", "required": True, "description": "SELECT 语句"}},
        )
        reg.register(
            self.submit_request,
            name="submit_request",
            description="提交申请单（写操作，走 L1 审批：提交后等待审批人批准才执行）。",
            schema={
                "req_type": {"type": "string", "required": True, "description": "申请类型，如 software_install / procurement / expense"},
                "payload": {"type": "string", "required": True, "description": "申请内容说明"},
            },
        )
        return reg
