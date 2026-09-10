"""Gateway: single entry that assembles routing + retry + fallback + metrics.

Design points (Ch11):
- fallback always marks `degraded=True` on the completion (silent degradation
  is forbidden — Ch10 failure case 3);
- every call appends a metrics record (jsonl) with model, tokens, latency,
  fallback flag — the seed of Ch36 observability.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field

from .base import Completion, LLMClient
from .retry import NonRetryableError, RetryPolicy, RetryableError, call_with_retry
from .router import RequestConstraints, Router, Tier


@dataclass
class GatewayConfig:
    router: Router
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    metrics_path: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class Gateway:
    def __init__(self, config: GatewayConfig):
        self.config = config
        if config.metrics_path:
            os.makedirs(os.path.dirname(config.metrics_path), exist_ok=True)

    def complete(
        self,
        messages: list[dict],
        *,
        constraints: RequestConstraints | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> Completion:
        constraints = constraints or RequestConstraints()
        chain = self.config.router.route(constraints)
        last_err: Exception | None = None

        for i, tier in enumerate(chain):
            try:
                t0 = time.perf_counter()
                completion = call_with_retry(
                    lambda: tier.provider.complete(messages, temperature=temperature, max_tokens=max_tokens),
                    self.config.retry,
                )
                latency_ms = (time.perf_counter() - t0) * 1000
                if i > 0:
                    completion.degraded = True  # fallback happened — must be visible
                self._record(tier, completion, latency_ms, ok=True)
                return completion
            except (RetryableError, NonRetryableError, Exception) as e:  # noqa: BLE001
                last_err = e
                self._record(tier, None, 0.0, ok=False, error=str(e))
                # non-retryable request errors (bad params) are not fixed by
                # another provider either — but auth/quota ARE. Keep falling
                # back for everything except nothing: simplicity over cleverness,
                # the caller still sees the final error.

        raise last_err if last_err else RuntimeError("empty fallback chain")

    def _record(self, tier: Tier, completion: Completion | None, latency_ms: float, *, ok: bool, error: str | None = None):
        rec = {
            "ts": time.time(),
            "tier": tier.name,
            "model": tier.provider.model if hasattr(tier.provider, "model") else "?",
            "ok": ok,
            "error": error,
            "latency_ms": round(latency_ms, 1),
            "degraded": bool(completion and completion.degraded),
            "prompt_tokens": completion.prompt_tokens if completion else 0,
            "completion_tokens": completion.completion_tokens if completion else 0,
        }
        if self.config.metrics_path:
            with self.config._lock:
                with open(self.config.metrics_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec
