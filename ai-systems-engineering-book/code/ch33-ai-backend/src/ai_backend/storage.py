"""Ch33 components: 存储 (MemoryStorage) + Session (SessionManager).

存储：任务态/结果引用的唯一权威（Worker 无状态——状态全在存储，Ch33 案例二的红利）。
Session：用户↔任务归属（会话态管理的最小形态）。
"""

from __future__ import annotations

import threading

from .jobs import Job


class MemoryStorage:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._cancel_flags: set[str] = set()
        self._lock = threading.Lock()

    def save(self, job: Job) -> Job:
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def require(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job is None:
            raise KeyError(f"unknown job: {job_id}")
        return job

    def update(self, job: Job) -> Job:
        return self.save(job)

    def request_cancel(self, job_id: str) -> None:
        with self._lock:
            self._cancel_flags.add(job_id)

    def cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cancel_flags

    def running_jobs(self) -> list[Job]:
        with self._lock:
            return [j for j in self._jobs.values() if j.status == "running"]

    def all_jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())


class SessionManager:
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self._index: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def register(self, job: Job) -> None:
        with self._lock:
            self._index.setdefault(job.session_id, []).append(job.id)

    def jobs_of(self, session_id: str) -> list[Job]:
        with self._lock:
            job_ids = list(self._index.get(session_id, []))
        return [j for j in (self.storage.get(jid) for jid in job_ids) if j is not None]
