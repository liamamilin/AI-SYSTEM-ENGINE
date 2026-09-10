"""Ch33 components: Agent Runtime + Worker.

Agent Runtime：任务的工作进程（Ch19 loop 的宿主位；本最小版 = 分步执行
goal，每步经模型网关调用一次模型、发 progress 事件、写存储进度）。
Worker：无状态执行骨架——从队列取 Job、交给 Runtime、有序取消（检查点
之间检查取消标志，不杀进程）与超时判定（failed，绝不挂死）。
"""

from __future__ import annotations

import threading
import time

from .events import EventStream
from .jobs import Job, JobQueue, transition
from .storage import MemoryStorage


class AgentRuntime:
    def __init__(self, gateway, storage: MemoryStorage, events: EventStream):
        self.gateway = gateway
        self.storage = storage
        self.events = events

    def execute(self, job: Job) -> Job:
        job = self.storage.require(job.id)
        transition(job, "running")
        self.storage.update(job)
        self.events.publish(job.id, "log", "started", goal=job.goal, steps=job.steps)

        deadline = time.monotonic() + job.timeout_seconds
        answer = ""
        try:
            for step in range(1, job.steps + 1):
                if self.storage.cancel_requested(job.id):
                    return self._finalize(job, "cancelled")
                if time.monotonic() > deadline:
                    return self._finalize(job, "failed", error=f"timeout after {job.timeout_seconds}s")
                completion = self.gateway.complete(
                    [{"role": "user", "content": f"[step {step}/{job.steps}] {job.goal}"}],
                    temperature=0.0, max_tokens=256,
                )
                answer = completion.text
                job.progress = round(step / job.steps, 3)
                if completion.degraded:
                    job.degraded = True
                self.storage.update(job)
                self.events.publish(job.id, "progress", step=step, of=job.steps, progress=job.progress)
                if job.step_seconds > 0:
                    time.sleep(job.step_seconds)
            return self._finalize(job, "done", result=answer)
        except Exception as e:  # noqa: BLE001 — worker 任何异常都必须终局（failed），不挂死
            return self._finalize(job, "failed", error=f"{type(e).__name__}: {e}")

    def _finalize(self, job: Job, status: str, *, error: str | None = None, result: str | None = None) -> Job:
        transition(job, status, error=error, result=result)
        self.storage.update(job)
        if status == "done":
            self.events.publish(job.id, "result", "done", result=result)
        elif status == "failed":
            self.events.publish(job.id, "error", "failed", error=error)
        else:
            self.events.publish(job.id, "log", "cancelled")
        return job


class Worker:
    """单 worker：dequeue → runtime.execute。无状态——扩容即加实例."""

    def __init__(self, queue: JobQueue, runtime: AgentRuntime):
        self.queue = queue
        self.runtime = runtime
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> Job | None:
        job_id = self.queue.dequeue(timeout=0)
        if job_id is None:
            return None
        job = self.runtime.storage.require(job_id)
        if job.is_final():
            return job
        return self.runtime.execute(job)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _loop(self):
        while not self._stop.is_set():
            self.run_once()
            if self.queue.depth() == 0:
                time.sleep(0.01)  # idle: avoid busy spin
