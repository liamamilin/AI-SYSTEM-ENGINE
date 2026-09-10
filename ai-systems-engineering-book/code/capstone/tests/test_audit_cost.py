"""Audit + cost tests: 审计记录完整性与成本记账（Ch36/Ch40）。"""

from __future__ import annotations

import pytest

from capstone.audit import AuditRecord
from capstone.cost import CostLedger, estimate_cost

from conftest import J, ScriptedClient, make_platform, make_users


def _write_task():
    p = make_platform()
    alice = make_users()["it_alice"]
    outcome = p.run_task(
        alice, "查软件安装流程并提交安装申请", "先检索，再帮我提交申请",
        client=ScriptedClient([
            J(tool="search_docs", arguments={"query": "非白名单软件怎么安装"}, state_update={"检索": "done"}),
            J(tool="submit_request", arguments={"req_type": "software_install", "payload": "IDE 安装申请"}),
            J(finish=True, answer="流程已查到，申请已提交等待审批。"),
        ]),
    )
    return p, outcome


def test_audit_record_complete_for_write_task():
    """一次写路径任务的审计字段全非空（审计完整率门禁）。"""
    p, outcome = _write_task()
    a = outcome.audit
    a.require_complete(strict=True)  # 不抛 = 完整
    for field in ("task_id", "ts", "user_id", "question_hash", "answer_id",
                  "retrieved_doc_ids", "denied_doc_ids", "clearance_touched",
                  "tool_calls", "approvals", "stop", "cost"):
        v = getattr(a, field)
        assert v, f"审计字段 {field} 为空"
    assert a.cost > 0 and a.cost_calls > 0


def test_audit_replay_contains_full_chain():
    """审计链可完整回放：谁/何时/问什么哈希/检索块/工具/审批。"""
    p, outcome = _write_task()
    text = outcome.audit.replay()
    for token in ("u001", "sha:", "search_docs", "submit_request", "pending", "工具", "审批"):
        assert token in text, f"回放缺少 {token}"


def test_audit_question_hashed_not_plaintext():
    """脱敏存储：问题只存哈希，不存原文。"""
    p, outcome = _write_task()
    a = outcome.audit
    assert "软件" not in a.question_hash and len(a.question_hash) == 16
    assert a.question_chars > 0


def test_audit_log_write_and_retrieve(tmp_path):
    p, outcome = _write_task()
    path = tmp_path / "audit.jsonl"
    assert p.audit_log.write(str(path)) == 1
    assert p.audit_log.get(outcome.task_id) is outcome.audit


def test_cost_ledger_estimates_by_tier_prices():
    """成本记账：token 用量 × tier 价格表；分 tier 汇总。"""
    ledger = CostLedger()
    ledger.record("t1", "standard", "qwen3.5:9b-mlx", 1000, 500)
    ledger.record("t1", "economy", "qwen2.5:3b", 2000, 1000)
    t1 = ledger.task_cost("t1")
    assert t1["calls"] == 2 and t1["prompt_tokens"] == 3000 and t1["completion_tokens"] == 1500
    assert t1["cost"] == pytest.approx(
        estimate_cost("standard", 1000, 500) + estimate_cost("economy", 2000, 1000)
    )
    assert ledger.total()["tasks"] == 1


def test_task_cost_recorded_in_audit():
    """平台把每任务成本写进审计（cost per task 可回答"钱花在哪个环节"）。"""
    p, outcome = _write_task()
    cost = p.ledger.task_cost(outcome.task_id)
    assert cost["calls"] == 3  # 两轮 loop + 状态提醒共 3 次模型调用
    assert outcome.audit.cost == pytest.approx(cost["cost"])


def test_audit_incomplete_strict_rejected():
    """审计门禁：strict 模式下字段缺失拒绝出平台。"""
    a = AuditRecord(task_id="t", ts="x", user_id="u", question_hash="h", answer_id="a")
    with pytest.raises(ValueError, match="不完整"):
        a.require_complete(strict=True)
    a.require_complete(strict=False)  # 非写路径允许链路字段为空
