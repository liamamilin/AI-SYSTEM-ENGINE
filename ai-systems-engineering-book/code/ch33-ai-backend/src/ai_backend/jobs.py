"""Ch33 component 3: Job 实体 + 状态机 + 内存队列.

状态机（Ch33 正文）: accepted -> queued -> running -> done | failed | cancelled
                     accepted | queued -> cancelled（排队即取消，直接终局）
状态迁移非法即拒绝（InvalidTransitionError）——状态机是契约不是惯例。
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from pydantic import BaseModel, Field

VALID_TRANSITIONS: dict[str, set[str]] = {
    "accepted": {"queued", "cancelled"},
    "queued": {"running", "cancelled"},
    "running": {"done", "failed", "cancelled"},
}
FINAL_STATUSES = {"done", "failed", "cancelled"}


class InvalidTransitionError(Exception):
    pass


class Job(BaseModel):
    id: str
    session_id: str
    goal: str
    kind: str = "long"                 # long | quick(as-queued fallback)
    status: str = "accepted"
    steps: int = 1
    step_seconds: float = 0.0          # per-step simulated duration (demo)
    timeout_seconds: float = 30.0      # job-level deadline
    progress: float = 0.0
    result: str | None = None
    error: str | None = None
    degraded: bool = False
    idempotency_key: str | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = 0.0

    def is_final(self) -> bool:
        return self.status in FINAL_STATUSES


def transition(job: Job, new_status: str, *, error: str | None = None, result: str | None = None) -> Job:
    if new_status not in VALID_TRANSITIONS.get(job.status, set()):
        raise InvalidTransitionError(f"illegal transition {job.status} -> {new_status} (job {job.id})")
    job.status = new_status
    job.updated_at = time.time()
    if error is not None:
        job.error = error
    if result is not None:
        job.result = result
    return job


def new_job(session_id: str, goal: str, *, kind: str = "long", steps: int = 1,
            step_seconds: float = 0.0, timeout_seconds: float = 30.0,
            idempotency_key: str | None = None) -> Job:
    return Job(
        id=uuid.uuid4().hex[:12],
        session_id=session_id,
        goal=goal,
        kind=kind,
        steps=steps,
        step_seconds=step_seconds,
        timeout_seconds=timeout_seconds,
        idempotency_key=idempotency_key,
    )


class JobQueue:
    """进程内 FIFO 队列（单机 demo 形态；生产版 = Redis/MQ，Ch34 展开队列语义）."""

    def __init__(self):
        self._items: deque[str] = deque()
        self._lock = threading.Lock()

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            self._items.append(job_id)

    def dequeue(self, timeout: float = 0.0) -> str | None:
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                if self._items:
                    return self._items.popleft()
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.005)

    def depth(self) -> int:
        with self._lock:
            return len(self._items)
