"""Platform tests: 降级触发、降级矩阵、ACL 集成、拒答、Job 化、全链路 mock 冒烟。"""

from __future__ import annotations

import pytest

from capstone.platform import GatewayLoopClient

from conftest import (
    J,
    FakeLLM,
    ScriptedClient,
    make_platform,
    make_users,
)

from model_gateway.base import FakeProvider
from model_gateway.gateway import Gateway, GatewayConfig
from model_gateway.router import Router, Tier

from ai_backend.jobs import InvalidTransitionError, new_job, transition


def test_degraded_fallback_propagates_to_audit():
    """降级触发：首选层故障 → 回退层接管 → degraded 标记贯穿到审计。"""
    outputs = [
        J(tool="search_docs", arguments={"query": "VPN 怎么连接"}),
        J(finish=True, answer="从 IT 门户下载客户端，用域账号登录 [1]。"),
    ]
    std = FakeProvider(fail_first=4, outputs=outputs)  # 首层耗尽重试（Ch10）后仍故障
    econ = FakeProvider(outputs=outputs)
    gw = Gateway(GatewayConfig(router=Router([
        Tier("standard", std, "standard", 0.0, "local"),
        Tier("economy", econ, "economy", 0.0, "local"),
    ])))
    p = make_platform(gateway=gw)
    outcome = p.run_task(
        make_users()["it_alice"], "在家怎么连内网？", "请查知识库后回答",
        client=GatewayLoopClient(gw),
    )
    assert outcome.degraded is True
    assert outcome.audit.degraded is True
    assert outcome.stop == "finished"


def test_model_chain_exhausted_degrades_to_queued_job():
    """降级矩阵：模型链全耗尽 → queue_later（明示降级 + Job 入队，绝不假装成功）。"""
    p = make_platform(llm=None)  # answer 路径无 LLM → 链耗尽
    p.llm = _AlwaysFailLLM()
    outcome = p.answer(make_users()["it_alice"], "VPN 怎么连接？")
    assert outcome.degraded and outcome.refused
    assert outcome.stop == "degraded_job_queued"
    job = p.jobs[outcome.job_id]
    assert job.status == "queued"  # Ch35 矩阵：排队稍后，可见降级
    stages = p.events.stages_of(job.id)
    assert "degraded" in stages and "queued" in stages


def test_answer_refuses_out_of_domain():
    """拒答路径是功能不是缺陷（域外 query → 不调 LLM 直接拒答）。"""
    llm = FakeLLM()
    p = make_platform(llm=llm)
    outcome = p.answer(make_users()["it_alice"], "竞品 X 的价格是多少？")
    assert outcome.refused is True
    assert "未找到" in outcome.answer
    assert llm.calls == []  # 拒答不烧模型调用


def test_answer_confidential_question_acl_filtered():
    """集成：员工问薪酬 → 密级块检索层滤除 → 绝不出现在 context/citations。"""
    p = make_platform()
    alice = make_users()["it_alice"]
    outcome = p.answer(alice, "P4 薪级带宽和调薪窗口是多少？")
    assert "salary" in outcome.audit.denied_doc_ids
    assert "salary" not in outcome.audit.retrieved_doc_ids
    assert all(c["chunk_id"].split("-")[0] != "salary" for c in outcome.citations)  # 引用即审计：出处=被授权的出处


def test_answer_with_citations_records_cost():
    """正常问答：带引用回答 + 审计 + 成本记账。"""
    p = make_platform()
    outcome = p.answer(make_users()["it_alice"], "非白名单软件怎么安装？")
    assert outcome.refused is False
    assert outcome.citations and outcome.citations[0]["source"].endswith(".md")
    assert outcome.cost["calls"] == 1 and outcome.cost["cost"] > 0
    assert "software" in outcome.audit.retrieved_doc_ids


def test_full_chain_mock_smoke_search_approve_answer():
    """全链路 mock 冒烟：检索 → 写提交 → 平台外审批 → 执行 → 审计可回放 → 成本。"""
    p = make_platform()
    alice = make_users()["it_alice"]
    outcome = p.run_task(
        alice, "查采购流程并提交显示器采购申请", "请开始",
        client=ScriptedClient([
            J(tool="search_docs", arguments={"query": "3000 元以上设备采购审批流程"}),
            J(tool="submit_request", arguments={"req_type": "procurement", "payload": "显示器采购申请"}),
            J(finish=True, answer="已查到流程并提交申请，等待审批。"),
        ]),
    )
    assert outcome.stop == "finished" and outcome.answer
    assert p.writes == []  # 审批前零副作用（红线）
    rid = outcome.pending_requests[0]
    with pytest.raises(Exception):
        p.raise_if_not_approved(rid)
    p.approve(outcome.task_id, rid, "it-manager", approve=True)
    assert p.writes[0]["approved_by"] == "it-manager"
    assert outcome.audit.require_complete(strict=True) is None  # 审计完整
    assert outcome.audit.cost > 0


def test_submit_job_and_run_state_machine():
    """Job 化（ch33 复用）：提交 → queued → 执行 → done；非法迁移拒绝。"""
    p = make_platform()
    job = p.submit_job(make_users()["it_alice"], "查 VPN 连接方法")
    assert job.status == "queued"
    done = p.run_pending_jobs()
    assert done[0].status == "done"
    assert done[0].result
    fresh = new_job("u001", "x")
    with pytest.raises(InvalidTransitionError):
        transition(fresh, "done")  # accepted -> done 非法


def test_loop_search_denied_docs_recorded():
    """工具路径的越权尝试也进审计（denied_doc_ids）。"""
    p = make_platform()
    guest = make_users()["guest"]
    outcome = p.run_task(
        guest, "查一下薪级带宽", "请开始",
        client=ScriptedClient([
            J(tool="search_docs", arguments={"query": "P4 薪级带宽 调薪窗口"}),
            J(finish=True, answer="抱歉，您没有权限查看相关内容。"),
        ]),
    )
    assert "salary" in outcome.audit.denied_doc_ids
    assert "salary" not in outcome.audit.retrieved_doc_ids


class _AlwaysFailLLM:
    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512):
        raise TimeoutError("all model tiers down")
