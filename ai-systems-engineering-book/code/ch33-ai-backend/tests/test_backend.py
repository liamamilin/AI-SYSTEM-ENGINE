"""Ch33 tests: mock 优先（不依赖真实 Ollama）—— FakeProvider/Gateway 组合。

覆盖：分流规则 / Job 状态机迁移（含非法迁移）/ 超时→failed /
降级两条路径（回退链 degraded、全层耗尽→排队降级）/ 事件顺序与回放 /
取消（排队+运行中有序撤退）/ 并发排队 / 会话归属。
"""

import time

import pytest

from model_gateway.base import FakeProvider
from model_gateway.gateway import Gateway, GatewayConfig
from model_gateway.retry import RetryPolicy
from model_gateway.router import Router, Tier

from ai_backend.api import SYNC_THRESHOLD_SECONDS, ApiLayer, TaskRequest, classify
from ai_backend.jobs import InvalidTransitionError, new_job, transition


# ---------- helpers ----------

class SlowProvider(FakeProvider):
    """FakeProvider + per-call latency（测超时/取消需要真实耗时）."""

    def __init__(self, seconds: float, **kw):
        super().__init__(**kw)
        self.seconds = seconds

    def complete(self, messages, *, temperature=0.0, max_tokens=512):
        time.sleep(self.seconds)
        return super().complete(messages, temperature=temperature, max_tokens=max_tokens)


class BoomProvider(FakeProvider):
    def complete(self, messages, *, temperature=0.0, max_tokens=512):
        raise RuntimeError("boom")


def make_gateway(*providers):
    tiers = [Tier(f"tier{i}", p, "standard" if i == 0 else "economy", 0.0, "local")
             for i, p in enumerate(providers)]
    return Gateway(GatewayConfig(
        router=Router(tiers),
        retry=RetryPolicy(max_attempts=2, base_delay=0.0, cap=0.0),
    ))


def make_backend(*providers, workers: int = 0) -> ApiLayer:
    api = ApiLayer(make_gateway(*providers))
    if workers:
        api.start_workers(workers)
    return api


LONG = TaskRequest(goal="8 分钟的深度分析", kind="long", steps=2)


# ---------- 分流规则 ----------

def test_classify_quick_small_goes_sync():
    assert classify(TaskRequest(goal="改个标题", est_seconds=1.0)) == "sync"


def test_classify_long_kind_always_job():
    assert classify(TaskRequest(goal="分析", kind="long", est_seconds=0.1)) == "job"


def test_classify_est_over_threshold_goes_job():
    assert classify(TaskRequest(goal="批处理", est_seconds=SYNC_THRESHOLD_SECONDS + 1)) == "job"


# ---------- 同步直答 ----------

def test_sync_direct_answer():
    api = make_backend(FakeProvider(["quick answer"]))
    result = api.handle("s1", TaskRequest(goal="改个标题"))
    assert result.route == "sync" and result.status == "answered"
    assert result.answer == "quick answer" and not result.degraded


# ---------- Job 提交与状态机 ----------

def test_submit_long_task_enqueued_not_executed():
    api = make_backend(FakeProvider())  # 无 worker：排队不是失败
    result = api.handle("s1", LONG)
    assert result.route == "job" and result.status == "queued"
    job = api.get_job(result.job_id)
    assert job.status == "queued" and job.result is None


def test_job_full_lifecycle_via_worker():
    api = make_backend(FakeProvider(["step answer"]), workers=1)
    result = api.handle("s1", LONG)
    assert api.wait_idle()
    job = api.get_job(result.job_id)
    assert job.status == "done" and job.progress == 1.0
    assert job.result == "step answer"
    assert api.events.stages_of(job.id) == ["accepted", "queued", "started", "done"]
    api.stop_workers()


def test_invalid_transitions_rejected():
    job = new_job("s", "g")
    with pytest.raises(InvalidTransitionError):
        transition(job, "done")            # accepted -> done 非法
    transition(job, "queued")
    transition(job, "running")
    transition(job, "done")
    with pytest.raises(InvalidTransitionError):
        transition(job, "running")          # 终局不可复活


# ---------- 幂等提交 ----------

def test_idempotent_submit_returns_same_job():
    api = make_backend(FakeProvider())
    req = TaskRequest(goal="分析", kind="long", idempotency_key="idem-1")
    r1 = api.submit("s1", req)
    r2 = api.submit("s1", req)
    assert r1.job_id == r2.job_id


# ---------- 超时 -> failed ----------

def test_timeout_job_fails():
    api = make_backend(SlowProvider(0.08), workers=1)
    req = TaskRequest(goal="很慢的任务", kind="long", steps=5, timeout_seconds=0.1)
    result = api.handle("s1", req)
    assert api.wait_idle()
    job = api.get_job(result.job_id)
    assert job.status == "failed"
    assert "timeout" in job.error
    assert "failed" in api.events.stages_of(job.id)
    api.stop_workers()


# ---------- 降级矩阵 ----------

def test_degradation_fallback_tier_marks_degraded():
    api = make_backend(FakeProvider(["stale"], fail_first=3), FakeProvider(["fallback answer"]))
    result = api.handle("s1", TaskRequest(goal="改个标题"))
    assert result.status == "answered" and result.degraded
    assert result.answer == "fallback answer"


def test_degradation_chain_exhausted_queues_job():
    down = FakeProvider(["x"], fail_first=10**6)
    api = make_backend(down, FakeProvider(["x"], fail_first=10**6), workers=1)
    result = api.handle("s1", TaskRequest(goal="改个标题"))
    assert result.status == "queued_later" and result.degraded
    degraded_events = [e for e in api.replay() if e.stage == "degraded"]
    assert degraded_events and degraded_events[0].payload["mode"] == "queue_later"
    # 降级后的 Job 诚实失败（全层仍宕机），绝不假装成功
    assert api.wait_idle()
    job = api.get_job(result.job_id)
    assert job.status == "failed" and job.error
    api.stop_workers()


# ---------- 事件流 ----------

def test_event_replay_filtered_and_ordered():
    api = make_backend(FakeProvider(["a"]))
    r1 = api.submit("s1", TaskRequest(goal="j1", kind="long"))
    r2 = api.submit("s2", TaskRequest(goal="j2", kind="long"))
    api.runtime.execute(api.storage.require(r1.job_id))
    only_j1 = api.events.replay(r1.job_id)
    assert all(e.job_id == r1.job_id for e in only_j1)
    assert [e.stage for e in only_j1 if e.stage] == ["accepted", "queued", "started", "done"]
    assert len(api.replay()) > len(only_j1)  # 全局回放包含 j2 事件


def test_job_failure_emits_failed_event():
    api = make_backend(BoomProvider())
    result = api.submit("s1", TaskRequest(goal="会炸的任务", kind="long"))
    api.runtime.execute(api.storage.require(result.job_id))
    job = api.get_job(result.job_id)
    assert job.status == "failed" and "boom" in job.error
    error_events = [e for e in api.events.replay(result.job_id) if e.type == "error"]
    assert error_events and error_events[0].stage == "failed"


# ---------- 取消 ----------

def test_cancel_queued_job():
    api = make_backend(FakeProvider())  # 无 worker，job 停在 queued
    result = api.submit("s1", TaskRequest(goal="排队中的任务", kind="long"))
    assert api.cancel(result.job_id)
    assert api.get_job(result.job_id).status == "cancelled"


def test_cancel_running_job_ordered_retreat():
    api = make_backend(SlowProvider(0.03), workers=1)
    result = api.submit("s1", TaskRequest(goal="长任务", kind="long", steps=20))
    job_id = result.job_id
    deadline = time.monotonic() + 2.0
    while api.get_job(job_id).status != "running" and time.monotonic() < deadline:
        time.sleep(0.005)
    assert api.cancel(job_id)              # 有序撤退：标志位，不杀进程
    deadline = time.monotonic() + 2.0
    while not api.get_job(job_id).is_final() and time.monotonic() < deadline:
        time.sleep(0.005)
    job = api.get_job(job_id)
    assert job.status == "cancelled"
    assert job.progress < 1.0              # 检查点之间停止，未跑完
    assert "cancelled" in api.events.stages_of(job_id)
    api.stop_workers()


# ---------- 并发排队 ----------

def test_concurrent_queueing_multiple_jobs():
    api = make_backend(FakeProvider(["done text"]), workers=2)
    results = [api.submit("s1", TaskRequest(goal=f"job{i}", kind="long")) for i in range(6)]
    assert api.wait_idle(timeout=15.0)
    jobs = [api.get_job(r.job_id) for r in results]
    assert all(j.status == "done" for j in jobs)
    assert len({j.id for j in jobs}) == 6
    api.stop_workers()


# ---------- Session（会话归属） ----------

def test_session_ownership():
    api = make_backend(FakeProvider())
    mine = [api.submit("u1", TaskRequest(goal=f"m{i}", kind="long")) for i in range(3)]
    api.submit("u2", TaskRequest(goal="other", kind="long"))
    jobs = api.sessions.jobs_of("u1")
    assert {j.id for j in jobs} == {r.job_id for r in mine}
    assert len(api.sessions.jobs_of("u2")) == 1
