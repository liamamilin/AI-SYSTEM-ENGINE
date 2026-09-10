"""Ch33 component 1: API 层 —— 分流 + 幂等提交 + 同步直答 + 任务接口三件套.

分流核心（本章分水岭）：HTTP 请求只负责提交与查询，不承载执行。
  classify(request) -> "sync" | "job"
    kind == "long"            -> job（显式声明优先）
    est_seconds > SYNC_THRESHOLD -> job（时间尺度超阈值必 Job 化）
    else                      -> sync（毫秒-秒级，同步直答）
降级路径（Ch35 矩阵）：同步直答网关全层失败 → 降级为入队稍后处理（可见）。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pydantic import BaseModel

from .degradation import DegradationMatrix
from .events import EventStream
from .jobs import FINAL_STATUSES, Job, JobQueue, new_job, transition
from .runtime import AgentRuntime, Worker
from .storage import MemoryStorage, SessionManager

SYNC_THRESHOLD_SECONDS = 5.0


class TaskRequest(BaseModel):
    goal: str
    kind: str = "quick"              # quick | long
    est_seconds: float = 1.0
    steps: int = 1
    step_seconds: float = 0.0
    timeout_seconds: float = 30.0
    idempotency_key: str | None = None


def classify(req: TaskRequest, sync_threshold: float = SYNC_THRESHOLD_SECONDS) -> str:
    if req.kind == "long":
        return "job"
    if req.est_seconds > sync_threshold:
        return "job"
    return "sync"


@dataclass
class SyncResult:
    route: str                       # sync | job
    status: str                      # answered | queued_later | queued
    answer: str | None = None
    job_id: str | None = None
    degraded: bool = False


class ApiLayer:
    def __init__(self, gateway, *, sync_threshold: float = SYNC_THRESHOLD_SECONDS,
                 matrix: DegradationMatrix | None = None):
        self.gateway = gateway
        self.sync_threshold = sync_threshold
        self.matrix = matrix or DegradationMatrix()
        self.storage = MemoryStorage()
        self.events = EventStream()
        self.queue = JobQueue()
        self.sessions = SessionManager(self.storage)
        self.runtime = AgentRuntime(gateway, self.storage, self.events)
        self._workers: list[Worker] = []
        self._seq = 0
        self._seq_lock = threading.Lock()

    # ---- 分流入口 ----
    def handle(self, session_id: str, req: TaskRequest) -> SyncResult:
        route = classify(req, self.sync_threshold)
        if route == "sync":
            return self._sync_answer(session_id, req)
        return self._submit(session_id, req)

    # ---- 同步直答（毫秒-秒级） ----
    def _sync_answer(self, session_id: str, req: TaskRequest) -> SyncResult:
        with self._seq_lock:
            self._seq += 1
            ref = f"sync-{self._seq}"
        self.events.publish(ref, "log", "accepted", goal=req.goal, route="sync")
        try:
            completion = self.gateway.complete(
                [{"role": "user", "content": req.goal}], temperature=0.0, max_tokens=256,
            )
            self.events.publish(ref, "result", "done", result=completion.text,
                                degraded=completion.degraded)
            return SyncResult("sync", "answered", answer=completion.text, degraded=completion.degraded)
        except Exception as e:  # noqa: BLE001 — 回退链耗尽 → 降级矩阵接管
            row = self.matrix.on_sync_total_failure()
            self.events.publish(ref, "error", "degraded",
                                fault="model_chain_exhausted", mode=row.mode, detail=str(e))
            sub = req.model_copy(update={"kind": "long"})
            result = self._submit(session_id, sub, degraded_note=row.user_visible)
            return SyncResult("sync", "queued_later", job_id=result.job_id, degraded=True)

    # ---- 任务接口三件套：submit / get / cancel ----
    def _submit(self, session_id: str, req: TaskRequest, degraded_note: str | None = None) -> SyncResult:
        # 幂等提交：同 key 返回同 job（客户端重试安全）
        if req.idempotency_key:
            for job in self.storage.all_jobs():
                if job.idempotency_key == req.idempotency_key:
                    return SyncResult("job", job.status, job_id=job.id)
        job = new_job(
            session_id, req.goal, kind="long", steps=max(1, req.steps),
            step_seconds=req.step_seconds, timeout_seconds=req.timeout_seconds,
            idempotency_key=req.idempotency_key,
        )
        self.storage.save(job)
        self.sessions.register(job)
        self.events.publish(job.id, "log", "accepted", goal=req.goal)
        transition(job, "queued")  # accepted -> queued（实体落存储即入队）
        self.events.publish(job.id, "log", "queued", note=degraded_note or "")
        self.queue.enqueue(job.id)
        return SyncResult("job", "queued", job_id=job.id)

    def submit(self, session_id: str, req: TaskRequest) -> SyncResult:
        return self._submit(session_id, req)

    def get_job(self, job_id: str) -> Job | None:
        return self.storage.get(job_id)

    def cancel(self, job_id: str) -> bool:
        """取消 = 有序撤退：queued 直改终局；running 置标志，runtime 在下一个检查点停."""
        job = self.storage.get(job_id)
        if job is None or job.is_final():
            return False
        if job.status == "queued":
            transition(job, "cancelled")
            self.storage.update(job)
            self.events.publish(job_id, "log", "cancelled", where="queue")
            return True
        self.storage.request_cancel(job_id)
        return True

    # ---- 事件通道（轮询形态；SSE/WebSocket 是同一事件流的传输层） ----
    def events_for(self, job_id: str):
        return self.events.replay(job_id)

    def replay(self):
        return self.events.replay()

    # ---- Worker 池 ----
    def start_workers(self, n: int = 1):
        for _ in range(n):
            worker = Worker(self.queue, self.runtime)
            worker.start()
            self._workers.append(worker)

    def stop_workers(self):
        for w in self._workers:
            w.stop()
        self._workers.clear()

    def wait_idle(self, timeout: float = 10.0) -> bool:
        """等待队列清空且无 running（测试/冒烟用）."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            pending = [j for j in self.storage.all_jobs()
                       if j.status not in FINAL_STATUSES]
            if self.queue.depth() == 0 and not pending:
                return True
            time.sleep(0.01)
        return False
