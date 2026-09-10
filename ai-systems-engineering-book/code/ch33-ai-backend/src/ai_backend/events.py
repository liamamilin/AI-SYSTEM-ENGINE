"""Ch33 component 7: EventStream (事件流).

Event contract (Ch33 正文): {type: progress|log|result|error, payload, ts}.
Lifecycle stages ride inside events: accepted/queued/started/done/failed/
cancelled/degraded. In-memory append-only log — replayable (SSE/WebSocket 的
进程内替身；生产版推给客户端，本版供轮询与测试回放).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

EVENT_TYPES = {"progress", "log", "result", "error"}
STAGES = {"accepted", "queued", "started", "done", "failed", "cancelled", "degraded"}


@dataclass
class Event:
    ts: float
    job_id: str
    type: str            # progress | log | result | error
    stage: str | None    # accepted | queued | started | done | failed | cancelled | degraded
    payload: dict = field(default_factory=dict)


class EventStream:
    def __init__(self):
        self._events: list[Event] = []
        self._lock = threading.Lock()

    def publish(self, job_id: str, type_: str, stage: str | None = None, **payload) -> Event:
        if type_ not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {type_}")
        if stage is not None and stage not in STAGES:
            raise ValueError(f"unknown stage: {stage}")
        event = Event(ts=time.time(), job_id=job_id, type=type_, stage=stage, payload=payload)
        with self._lock:
            self._events.append(event)
        return event

    def replay(self, job_id: str | None = None) -> list[Event]:
        """Replay the event log (optionally filtered by job) — 轮询/回放通道."""
        with self._lock:
            events = list(self._events)
        return [e for e in events if job_id is None or e.job_id == job_id]

    def stages_of(self, job_id: str) -> list[str]:
        return [e.stage for e in self.replay(job_id) if e.stage is not None]
