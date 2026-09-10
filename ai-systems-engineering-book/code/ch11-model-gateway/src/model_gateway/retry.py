"""Ch10 reliability layer: typed retry policy with backoff + jitter.

Retriable = (429-like, timeout, transient-5xx). NOT retriable: 400-class,
auth/quota-exhausted, content-filtered. Callers raise typed errors; the
policy decides.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


class RetryableError(Exception): ...


class NonRetryableError(Exception): ...


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.2
    cap: float = 3.0
    jitter: float = 0.5  # uniform(1-j, 1+j) multiplier

    def delay_for(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.cap)
        return delay * random.uniform(1 - self.jitter, 1 + self.jitter)


def call_with_retry(fn, policy: RetryPolicy | None = None) -> object:
    """fn() -> result; raises RetryableError/NonRetryableError as classified."""
    policy = policy or RetryPolicy()
    last: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except NonRetryableError:
            raise
        except (RetryableError, TimeoutError, ConnectionError) as e:
            last = e
            if attempt == policy.max_attempts:
                break
            time.sleep(policy.delay_for(attempt))
    raise RetryableError(f"failed after {policy.max_attempts} attempts: {last}")
