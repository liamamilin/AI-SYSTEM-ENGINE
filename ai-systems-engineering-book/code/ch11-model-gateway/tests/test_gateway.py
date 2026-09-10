"""Tests: routing, retry, fallback marking, metrics (all mocked)."""

import json

import pytest

from model_gateway.base import FakeProvider
from model_gateway.gateway import Gateway, GatewayConfig
from model_gateway.retry import NonRetryableError, RetryPolicy, RetryableError, call_with_retry
from model_gateway.router import RequestConstraints, Router, Tier


def make_tiers(tmp_path):
    cloud = Tier("cloud-strong", FakeProvider(["cloud answer"]), quality="high", cost_per_1k=3.0, privacy="cloud")
    local = Tier("local-9b", FakeProvider(["local answer"]), quality="standard", cost_per_1k=0.0, privacy="local")
    return cloud, local


def test_route_prefers_quality_order():
    cloud, local = make_tiers(None)
    router = Router([local, cloud])
    chain = router.route(RequestConstraints())
    assert chain[0].name == "cloud-strong"


def test_route_privacy_local_only():
    cloud, local = make_tiers(None)
    router = Router([cloud, local])
    chain = router.route(RequestConstraints(privacy_local_only=True))
    assert [t.name for t in chain] == ["local-9b"]


def test_route_privacy_violation_raises():
    cloud, _ = make_tiers(None)
    router = Router([cloud])
    with pytest.raises(ValueError):
        router.route(RequestConstraints(privacy_local_only=True))


def test_route_economy_orders_by_cost():
    cloud, local = make_tiers(None)
    router = Router([cloud, local])
    chain = router.route(RequestConstraints(prefer_economy=True))
    assert chain[0].name == "local-9b"


def test_retry_succeeds_on_transient():
    p = FakeProvider(["ok"], fail_first=1)
    out = call_with_retry(lambda: p.complete([{"role": "user", "content": "x"}]), RetryPolicy(base_delay=0.01))
    assert out.text == "ok"


def test_retry_gives_up_after_max_attempts():
    p = FakeProvider(["ok"], fail_first=99)
    with pytest.raises(RetryableError):
        call_with_retry(lambda: p.complete([{"role": "user", "content": "x"}]), RetryPolicy(max_attempts=2, base_delay=0.01))
    assert p.calls == 2


def test_non_retryable_fails_fast():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise NonRetryableError("bad params")

    with pytest.raises(NonRetryableError):
        call_with_retry(fn, RetryPolicy(base_delay=0.01))
    assert calls["n"] == 1


def test_gateway_fallback_marks_degraded(tmp_path):
    cloud, local = make_tiers(tmp_path)
    cloud.provider = FakeProvider(["cloud answer"], fail_first=99)  # cloud down
    gw = Gateway(GatewayConfig(router=Router([cloud, local]), retry=RetryPolicy(max_attempts=2, base_delay=0.01)))
    out = gw.complete([{"role": "user", "content": "hi"}])
    assert out.text == "local answer"
    assert out.degraded is True  # THE rule: fallback must be visible


def test_gateway_no_degradation_on_first_tier(tmp_path):
    cloud, local = make_tiers(tmp_path)
    gw = Gateway(GatewayConfig(router=Router([cloud, local]), retry=RetryPolicy(max_attempts=2, base_delay=0.01)))
    out = gw.complete([{"role": "user", "content": "hi"}])
    assert out.degraded is False


def test_gateway_metrics_written(tmp_path):
    cloud, local = make_tiers(tmp_path)
    metrics = tmp_path / "metrics.jsonl"
    gw = Gateway(GatewayConfig(router=Router([cloud, local]), retry=RetryPolicy(base_delay=0.01), metrics_path=str(metrics)))
    gw.complete([{"role": "user", "content": "hi"}])
    recs = [json.loads(l) for l in metrics.read_text().splitlines()]
    assert len(recs) == 1
    assert recs[0]["ok"] is True and recs[0]["tier"] == "cloud-strong"
    assert "degraded" in recs[0] and "latency_ms" in recs[0]


def test_gateway_all_tiers_down_raises(tmp_path):
    cloud, local = make_tiers(tmp_path)
    cloud.provider = FakeProvider([], fail_first=99)
    local.provider = FakeProvider([], fail_first=99)
    gw = Gateway(GatewayConfig(router=Router([cloud, local]), retry=RetryPolicy(max_attempts=1)))
    with pytest.raises(Exception):
        gw.complete([{"role": "user", "content": "hi"}])
