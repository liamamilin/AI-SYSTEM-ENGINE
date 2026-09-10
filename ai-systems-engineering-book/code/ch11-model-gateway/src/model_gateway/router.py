"""Routing: pick a model tier by declared task constraints (Ch11 decision model).

Tiers are declared in configs/gateway.toml. Router only chooses among
healthy, available tiers that satisfy the request's constraints.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Tier:
    name: str
    provider: object  # LLMClient
    quality: str      # "high" | "standard" | "economy"
    cost_per_1k: float
    privacy: str      # "local" | "cloud"
    enabled: bool = True


@dataclass
class RequestConstraints:
    privacy_local_only: bool = False
    prefer_quality: bool = False
    prefer_economy: bool = False


QUALITY_ORDER = {"high": 0, "standard": 1, "economy": 2}


class Router:
    def __init__(self, tiers: list[Tier]):
        self.tiers = [t for t in tiers if t.enabled]

    def route(self, c: RequestConstraints) -> list[Tier]:
        """Ordered candidate list: best match first; rest are fallback chain."""
        pool = self.tiers
        if c.privacy_local_only:
            pool = [t for t in pool if t.privacy == "local"]
            if not pool:
                raise ValueError("no local tier available for privacy_local_only request")
        if c.prefer_quality:
            pool = sorted(pool, key=lambda t: (QUALITY_ORDER[t.quality], t.cost_per_1k))
        elif c.prefer_economy:
            pool = sorted(pool, key=lambda t: (t.cost_per_1k, QUALITY_ORDER[t.quality]))
        else:
            pool = sorted(pool, key=lambda t: QUALITY_ORDER[t.quality])
        return pool
