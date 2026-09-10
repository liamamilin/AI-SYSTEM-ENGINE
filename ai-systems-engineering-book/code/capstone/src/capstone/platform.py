"""Ch60 capstone — platform: 组装层。

把 ch11（网关 tier 路由）+ ch08/19（手写 Agent Loop，加审批位）+ ch29（七环 RAG，
语料换成 capstone 领域）+ ch33（Job 化 + 降级矩阵）+ eval-runner 的基础设施
接成一次完整任务链路：检索（ACL 过滤）→（写路径 L1 审批）→ 回答 → 审计 → 成本。

组装不重写：本文件只有"接线"与任务编排，机制全部来自各章已验证代码
（接口稳定、实现可换——capstone 要验证的正是这些稳定抽象）。
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field

from agent_loop import AgentLoop
from ai_backend.events import EventStream
from ai_backend.jobs import Job, JobQueue, new_job, transition
from model_gateway.router import RequestConstraints
from rag_pipeline.corpus import RawDoc
from rag_pipeline.generation import REFUSAL_TEXT, generate, refuse as rag_refuse
from rag_pipeline.pipeline import RagConfig, RagPipeline
from rag_pipeline.retrieval import retrieve
from tool_calling.registry import ToolRegistry

from .audit import AuditLog, AuditRecord
from .cost import CostLedger
from .security import AccessRule, CLEARANCE_LEVELS, CapabilityTable, UserContext, acl_filter
from .tools import ApprovalGate, PendingRequest, ToolHost

# ---------------------------------------------------------------------------
# Capstone 语料（内部知识助手域，3 密级 × 多部门）——复用 ch29 RawDoc 结构，
# 七环管道零改动（接口稳定、实现可换）。
# ---------------------------------------------------------------------------

HEADER = "【IT 服务台知识库 · 内部资料 · 请勿外传】"
FOOTER = "第 1 页 / 共 1 页 · 打印无效"

CAPSTONE_DOCS: list[RawDoc] = [
    RawDoc(
        doc_id="vpn", source="kb_vpn.md", date="2026-08-01", acl="public",
        pages=[f"{HEADER}\n## VPN 连接\n在家办公需先连接 VPN 才能访问内网系统：从 IT 门户下载客户端，用域账号登录即可。\n\n## 办公 Wi-Fi\n办公区 Wi-Fi 分为 CORP（域设备专用）与 GUEST（访客）两个网络，访客网络无法访问内网打印机。\n\n{FOOTER}"],
    ),
    RawDoc(
        doc_id="password", source="kb_password.md", date="2026-08-01", acl="public",
        pages=[f"{HEADER}\n## 密码重置\n忘记域账号密码可在自助平台用绑定手机重置；连续 5 次输错账号将锁定 30 分钟。\n\n## 账号解锁\n锁定到期自动解锁；紧急情况可联系 IT 服务台人工解锁（需本人工卡验证）。\n\n{FOOTER}"],
    ),
    RawDoc(
        doc_id="software", source="kb_software_install.md", date="2026-08-10", acl="internal",
        pages=[f"{HEADER}\n## 软件安装申请\n非白名单软件需在 ITSM 提交安装申请（附软件用途说明），IT 审批后 1 个工作日内由桌面运维远程安装；员工不得自行安装未授权软件。\n\n## 正版许可\n研发类工具由部门统一采购许可证，申请时需填写成本中心。\n\n{FOOTER}"],
    ),
    RawDoc(
        doc_id="expense", source="kb_expense.md", date="2026-07-20", acl="internal",
        pages=[f"{HEADER}\n## 差旅报销\n差旅结束后 15 天内在财务系统提交报销，机票酒店需发票与行程单一致；单笔超过 5000 元需部门总监加签。\n\n## 报销标准\n市内交通实报实销，餐补每天 100 元封顶。\n\n{FOOTER}"],
    ),
    RawDoc(
        doc_id="salary", source="kb_salary_band.md", date="2026-06-30", acl="confidential",
        pages=[f"{HEADER}\n## 薪级带宽\nP4 薪级年带宽 30-45 万，P5 为 45-70 万。\n\n## 调薪窗口\n调薪窗口为每年 4 月与 10 月，普通调薪幅度不超过带宽 15%，超出需 HRVP 特批。\n\n{FOOTER}"],
    ),
    RawDoc(
        doc_id="server_ops", source="kb_server_ops.md", date="2026-08-15", acl="confidential",
        pages=[f"{HEADER}\n## 生产变更窗口\n生产环境变更只允许在周二/周四 22:00-24:00 窗口执行，需变更单与双人复核。\n\n## 数据库权限\n生产数据库仅 DBA 组可直连；开发人员经审计网关跳板查询只读副本。\n\n{FOOTER}"],
    ),
    RawDoc(
        doc_id="procurement", source="kb_procurement.md", date="2026-07-01", acl="internal",
        pages=[f"{HEADER}\n## 采购申请\n单价 3000 元以上的设备采购需在 ITSM 提交采购申请，经部门负责人与 IT 资产管理员双重审批后由采购部下单。\n\n## 资产领用\n新员工标准配置为笔记本 1 台加显示器 1 台，超出标准需部门负责人审批。\n\n{FOOTER}"],
    ),
]

CAPSTONE_ACL: dict[str, AccessRule] = {
    r.doc_id: r
    for r in [
        AccessRule(doc_id="vpn", clearance="public", departments=set()),
        AccessRule(doc_id="password", clearance="public", departments=set()),
        AccessRule(doc_id="software", clearance="internal", departments={"it", "engineering"}),
        AccessRule(doc_id="expense", clearance="internal", departments={"finance", "hr"}),
        AccessRule(doc_id="salary", clearance="confidential", departments={"hr"}),
        AccessRule(doc_id="server_ops", clearance="confidential", departments={"it"}),
        AccessRule(doc_id="procurement", clearance="internal", departments={"finance", "it", "engineering"}),
    ]
}

# query_db 只读 mock 库（工单/资产两张表）
MOCK_DB: dict[str, list[dict]] = {
    "asset": [
        {"asset_id": "A-1001", "type": "显示器", "owner": "u001", "status": "in_use"},
        {"asset_id": "A-1002", "type": "笔记本", "owner": "u002", "status": "in_use"},
        {"asset_id": "A-1003", "type": "显示器", "owner": "u003", "status": "spare"},
    ],
    "request": [
        {"request_id": "R-5001", "type": "software_install", "applicant": "u001", "status": "approved"},
        {"request_id": "R-5002", "type": "procurement", "applicant": "u002", "status": "pending"},
    ],
}


def toy_embed_fn(dim: int = 64):
    """确定性 mock embedding（字符 bigram 哈希到固定维）——测试与 mock 评测用。"""
    import math
    import re

    def embed(texts: list[str]) -> list[list[float]]:
        vecs = []
        for t in texts:
            grams = [t[i:i + 2] for i in range(len(t) - 1)] + re.findall(r"[a-zA-Z0-9]+", t)
            v = [0.0] * dim
            for g in grams:
                v[hash(g) % dim] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vecs.append([x / norm for x in v])
        return vecs

    return embed


# ---------------------------------------------------------------------------
# 平台
# ---------------------------------------------------------------------------


@dataclass
class SearchOutcome:
    allowed_hits: list
    allowed_ids: list[str]
    denied_ids: list[str]
    snippets: list[dict]
    max_score: float


@dataclass
class TaskOutcome:
    task_id: str
    answer: str | None = None
    refused: bool = False
    degraded: bool = False
    stop: str = ""
    audit: AuditRecord | None = None
    cost: dict = field(default_factory=dict)
    citations: list[dict] = field(default_factory=list)
    pending_requests: list[str] = field(default_factory=list)
    job_id: str | None = None
    loop: object | None = None


class CostTrackingClient:
    """给任意 ch08/ch19 协议 client 挂上 per-task 成本记账（包装，不改动）。"""

    def __init__(self, base, ledger: CostLedger, task_id: str, tier: str = "standard"):
        self.base = base
        self.ledger = ledger
        self.task_id = task_id
        self.tier = tier
        self.degraded = False

    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512):
        c = self.base.complete(messages, temperature=temperature, max_tokens=max_tokens)
        self.degraded = self.degraded or bool(getattr(c, "degraded", False))
        self.ledger.record(
            self.task_id, self.tier, getattr(c, "model", "") or "unknown",
            getattr(c, "prompt_tokens", 0) or 0, getattr(c, "completion_tokens", 0) or 0,
        )
        return c


class GatewayLoopClient:
    """把 ch11 网关适配成 ch19 loop 的 client 协议（enterprise 请求隐私本地硬约束）。"""

    def __init__(self, gateway, *, privacy_local_only: bool = True, tier_label: str = "standard"):
        self.gateway = gateway
        self.privacy_local_only = privacy_local_only
        self.tier_label = tier_label

    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512):
        c = self.gateway.complete(
            messages,
            constraints=RequestConstraints(privacy_local_only=self.privacy_local_only),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _SimpleCompletion(c.text, c.prompt_tokens, c.completion_tokens, c.degraded, c.model)


@dataclass
class _SimpleCompletion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    degraded: bool = False
    model: str = ""


class KnowledgePlatform:
    """内部知识助手平台（任务 A）：RAG + 权限 + 审计的最小生产骨架。"""

    def __init__(
        self,
        embed_fn,
        llm=None,
        *,
        gateway=None,
        docs: list[RawDoc] | None = None,
        acl: dict[str, AccessRule] | None = None,
        refuse_threshold: float = 0.45,
        top_k: int = 6,
        alpha: float = 0.6,
        rag_tier: str = "standard",
        loop_tier: str = "standard",
    ):
        self.pipeline = RagPipeline(
            embed_fn=embed_fn, llm=llm,
            raw_docs=docs or CAPSTONE_DOCS,
            config=RagConfig(refuse_threshold=refuse_threshold, top_k=top_k, alpha=alpha),
        )
        self.embed_fn = embed_fn
        self.llm = llm
        self.gateway = gateway
        self.rules = dict(acl or CAPSTONE_ACL)
        self.rag_tier = rag_tier
        self.loop_tier = loop_tier
        # 入库门禁（ch59 红线）：索引里每个 doc 必须有完整 ACL，否则拒绝启动
        for chunk in self.pipeline.index.chunks.values():
            rule = self.rules.get(chunk.doc_id)
            if rule is None:
                raise RuntimeError(f"fail-closed：文档 {chunk.doc_id} 无 ACL 规则，拒绝入索引")
        self.audit_log = AuditLog()
        self.ledger = CostLedger()
        self.gate = ApprovalGate(executor=self._apply_write)
        self.writes: list[dict] = []  # 写副作用落地处（mock 工单系统）
        self.queue = JobQueue()
        self.events = EventStream()
        self.jobs: dict[str, Job] = {}

    # ---- 检索（七环 rings 1-5 已建，rings 6 + ACL 过滤在此） ----
    def search(self, user: UserContext, question: str, *, top_k: int | None = None) -> SearchOutcome:
        cfg = self.pipeline.config
        qv = self.embed_fn([question])[0]
        hits = retrieve(
            question, self.pipeline.index, qv,
            top_k=top_k or cfg.top_k, alpha=cfg.alpha,
            bm25_saturation=cfg.bm25_saturation,
        )
        max_score = hits[0].score if hits else 0.0
        allowed, denied = acl_filter(hits, user, self.rules)  # 检索层过滤（ch59 红线）
        allowed_ids = list(dict.fromkeys(h.chunk.doc_id for h in allowed))  # 去重（块级→文档级）
        denied_ids = list(dict.fromkeys(denied))
        snippets = [
            {
                "n": i,
                "doc_id": h.chunk.doc_id,
                "source": h.chunk.meta.source if h.chunk.meta else "unknown",
                "section": h.chunk.section,
                "text": (h.parent.text if h.parent else h.chunk.text)[:400],
            }
            for i, h in enumerate(allowed, 1)
        ]
        return SearchOutcome(allowed, allowed_ids, denied_ids, snippets, max_score)

    def query_db(self, sql: str) -> list[dict]:
        import re

        m = re.search(r"\bfrom\s+([a-zA-Z_]\w*)", sql, re.IGNORECASE)
        table = m.group(1).lower() if m else ""
        if table not in MOCK_DB:
            raise ValueError(f"未知表: {table!r}（可用: {sorted(MOCK_DB)}）")
        return MOCK_DB[table][:5]

    # ---- 直接问答链路：检索 →（ACL）→ 生成/拒答 → 审计 → 成本 ----
    def answer(self, user: UserContext, question: str) -> TaskOutcome:
        task_id = uuid.uuid4().hex[:12]
        audit = self._new_audit(task_id, user, question)
        tracked = CostTrackingClient(self.llm, self.ledger, task_id, tier=self.rag_tier)
        try:
            out = self.search(user, question)
            audit.retrieved_doc_ids = out.allowed_ids
            audit.denied_doc_ids = out.denied_ids
            audit.clearance_touched = self._max_clearance(out.allowed_ids)
            if not out.allowed_hits or out.max_score < self.pipeline.config.refuse_threshold:
                ans = rag_refuse(question, f"max_score={out.max_score:.3f} 低于阈值或来源被权限过滤")
                audit.refused = True
            else:
                ans = generate(question, out.allowed_hits, tracked, max_tokens=512)
            answer_id = "ans-" + hashlib.sha1(ans.text.encode()).hexdigest()[:8]
            audit.answer_id, audit.refused = answer_id, ans.refused
            cost = self.ledger.task_cost(task_id)
            audit.cost, audit.cost_calls = cost["cost"], cost["calls"]
            audit.require_complete(strict=False)  # 问答路径：链路字段按非写任务校验
            self.audit_log.append(audit)
            return TaskOutcome(task_id=task_id, answer=ans.text, refused=ans.refused,
                               audit=audit, cost=cost,
                               citations=[c.model_dump() for c in ans.citations])
        except Exception as e:  # noqa: BLE001 — 模型链耗尽 → 降级矩阵（Ch35）
            return self._degrade_to_job(user, question, task_id, audit, reason=str(e))

    # ---- Agent 任务链路：loop + 3 工具（写路径 L1 审批）+ 审计 + 成本 ----
    def run_task(
        self, user: UserContext, goal: str, user_input: str, *,
        client=None, approver: str | None = None, max_rounds: int = 6,
    ) -> TaskOutcome:
        task_id = uuid.uuid4().hex[:12]
        audit = self._new_audit(task_id, user, goal)
        host = ToolHost(self, user)
        decisions_before = len(self.gate.decisions)
        base = client or (self.gateway and GatewayLoopClient(self.gateway)) or self.llm
        tracked = CostTrackingClient(base, self.ledger, task_id, tier=self.loop_tier)
        try:
            result = AgentLoop(host.build_registry(), max_rounds=max_rounds).run(tracked, goal, user_input)
        except Exception as e:  # noqa: BLE001 — 模型链耗尽 → 降级矩阵（Ch35）
            return self._degrade_to_job(user, goal, task_id, audit, reason=str(e))
        if approver:  # 审批位（Ch25）：写请求在此决断，副作用仍只经 gate
            for rid in host.submitted:
                if self.gate.get(rid) and self.gate.get(rid).status == "pending":
                    self.gate.decide(rid, approver, approve=True)
        audit.retrieved_doc_ids = host.used_docs
        audit.denied_doc_ids = host.denied_docs
        audit.clearance_touched = self._max_clearance(host.used_docs)
        audit.tool_calls = [
            {"round": t.get("round"), "tool": t.get("tool"), "ok": t.get("ok"), "error": t.get("error")}
            for t in result.trace
        ]
        audit.approvals = [{"request_id": r, "decision": "pending"} for r in host.submitted] + self.gate.decisions[decisions_before:]
        audit.stop = result.stop
        audit.degraded = tracked.degraded
        audit.refused = (result.answer is None)
        audit.answer_id = "ans-" + hashlib.sha1((result.answer or "").encode()).hexdigest()[:8]
        cost = self.ledger.task_cost(task_id)
        audit.cost, audit.cost_calls = cost["cost"], cost["calls"]
        if host.submitted:
            audit.require_complete(strict=True)  # 写路径：审计链必须完整才出平台
        else:
            audit.require_complete(strict=False)
        self.audit_log.append(audit)
        return TaskOutcome(
            task_id=task_id, answer=result.answer, stop=result.stop, audit=audit,
            cost=cost, degraded=tracked.degraded, pending_requests=list(host.submitted), loop=result,
        )

    # ---- 审批决断（平台入口：审计同步落账） ----
    def approve(self, task_id: str, request_id: str, approver: str, *, approve: bool = True) -> dict:
        decision = self.gate.decide(request_id, approver, approve=approve)
        audit = self.audit_log.get(task_id)
        if audit is not None:
            audit.approvals.append({
                "request_id": request_id, "approver": approver,
                "decision": "approved" if approve else "rejected",
                **decision.get("effect", {}),
            })
        return decision

    def raise_if_not_approved(self, request_id: str) -> None:
        """红线显式拒绝路径：未经 L1 审批请求执行写操作 → ApprovalRequiredError。"""
        self.gate.raise_if_not_approved(request_id)

    # ---- Job 化（ch33 复用：状态机 + 队列 + 事件流）与降级矩阵（Ch35） ----
    def submit_job(self, user: UserContext, goal: str) -> Job:
        job = new_job(user.user_id, goal, kind="long")
        self.jobs[job.id] = job
        transition(job, "queued")
        self.events.publish(job.id, "log", "accepted", goal=goal)
        self.events.publish(job.id, "log", "queued")
        self.queue.enqueue(job.id)
        return job

    def run_pending_jobs(self, *, approver: str | None = None) -> list[Job]:
        done: list[Job] = []
        while True:
            job_id = self.queue.dequeue(timeout=0)
            if job_id is None:
                break
            job = self.jobs[job_id]
            transition(job, "running")
            self.events.publish(job.id, "log", "started", goal=job.goal)
            try:
                outcome = self.run_task(UserContext(user_id=job.session_id, clearance="internal", departments={"it"}), job.goal, job.goal, approver=approver)
                transition(job, "done", result=outcome.answer or "(no answer)")
                self.events.publish(job.id, "result", "done", result=job.result)
            except Exception as e:  # noqa: BLE001 — worker 任何异常都必须终局，不挂死
                transition(job, "failed", error=f"{type(e).__name__}: {e}")
                self.events.publish(job.id, "error", "failed", error=job.error)
            done.append(job)
        return done

    # ---- 内部 ----
    def _new_audit(self, task_id: str, user: UserContext, question: str) -> AuditRecord:
        return AuditRecord(
            task_id=task_id,
            ts=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            user_id=user.user_id,
            question_hash=hashlib.sha256(question.encode()).hexdigest()[:16],
            question_chars=len(question),
        )

    def _max_clearance(self, doc_ids: list[str]) -> str:
        levels = [CLEARANCE_LEVELS[self.rules[d].clearance] for d in doc_ids if d in self.rules]
        return {v: k for k, v in CLEARANCE_LEVELS.items()}[max(levels)] if levels else "none"

    def _apply_write(self, req: PendingRequest) -> dict:
        """写副作用唯一入口（只有 ApprovalGate.approve 路径会调用）。"""
        ticket = f"T-{len(self.writes) + 1:04d}"
        self.writes.append({
            "ticket": ticket, "type": req.req_type, "payload": req.payload,
            "user": req.user_id, "ts": time.time(), "approved_by": req.decided_by,
        })
        return {"ticket": ticket, "status": "submitted"}

    def _degrade_to_job(self, user: UserContext, goal: str, task_id: str, audit: AuditRecord, *, reason: str) -> TaskOutcome:
        """模型链耗尽 → 降级矩阵 queue_later：明示降级，绝不假装成功（Ch35/Ch33）。"""
        job = self.submit_job(user, goal)
        self.events.publish(job.id, "error", "degraded", fault="model_chain_exhausted", mode="queue_later", detail=reason, task_id=task_id)
        audit.degraded = True
        audit.stop = "degraded_job_queued"
        audit.refused = True
        audit.answer_id = "ans-degraded-" + job.id
        cost = self.ledger.task_cost(task_id)
        audit.cost, audit.cost_calls = cost["cost"], cost["calls"]
        audit.require_complete(strict=False)
        self.audit_log.append(audit)
        return TaskOutcome(task_id=task_id, answer=None, refused=True, degraded=True,
                           stop="degraded_job_queued", audit=audit, cost=cost, job_id=job.id)
