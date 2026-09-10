"""Approval / tools tests: 写工具未经 L1 审批绝不执行（Ch60 红线）。"""

from __future__ import annotations

import pytest

from capstone.tools import ApprovalGate, ApprovalRequiredError, PendingRequest

from conftest import J, ScriptedClient, make_platform, make_users


def test_write_tool_without_approval_never_executes():
    """红线断言一：未审批 → 副作用 store 为空 + 显式拒绝执行。"""
    p = make_platform()
    alice = make_users()["it_alice"]
    outcome = p.run_task(
        alice, "为工位申请一台显示器", "请提交采购申请",
        client=ScriptedClient([
            J(tool="submit_request", arguments={"req_type": "procurement", "payload": "工位显示器 1 台"}),
            J(finish=True, answer="已提交采购申请，等待审批。"),
        ]),
    )
    assert outcome.pending_requests  # 提交成功（挂起）
    assert p.writes == []  # 未审批 → 没有任何写副作用
    rid = outcome.pending_requests[0]
    with pytest.raises(ApprovalRequiredError):
        p.raise_if_not_approved(rid)  # 直接执行请求 → 显式拒绝


def test_write_tool_executes_only_after_approval():
    """红线断言二：审批后 → 副作用落地 + 审计记录审批决定。"""
    p = make_platform()
    alice = make_users()["it_alice"]
    outcome = p.run_task(
        alice, "为工位申请一台显示器", "请提交采购申请",
        client=ScriptedClient([
            J(tool="submit_request", arguments={"req_type": "procurement", "payload": "工位显示器 1 台"}),
            J(finish=True, answer="已提交采购申请，等待审批。"),
        ]),
    )
    rid = outcome.pending_requests[0]
    decision = p.approve(outcome.task_id, rid, "it-manager", approve=True)
    assert decision["status"] == "executed"
    assert len(p.writes) == 1 and p.writes[0]["ticket"] == "T-0001"  # 批准后才执行
    assert any(a["decision"] == "approved" for a in outcome.audit.approvals)  # 审批进审计链
    # 幂等：重复提交同内容 → 同 request_id
    gate = p.gate
    req = gate.submit("u001", "procurement", "工位显示器 1 台")
    assert req.request_id == rid


def test_rejected_write_never_executes():
    """审批人驳回 → 永不执行。"""
    p = make_platform()
    gate = p.gate
    req = gate.submit("u001", "expense", "超标餐补报销")
    gate.decide(req.request_id, "finance-lead", approve=False)
    assert gate.get(req.request_id).status == "rejected"
    with pytest.raises(ApprovalRequiredError):
        gate.raise_if_not_approved(req.request_id)
    assert p.writes == []


def test_gate_decide_twice_rejected():
    """终态请求不可再次决断（状态机语义）。"""
    gate = ApprovalGate(executor=lambda r: {})
    req = gate.submit("u", "t", "p")
    gate.decide(req.request_id, "a", approve=False)
    with pytest.raises(ValueError):
        gate.decide(req.request_id, "a", approve=True)


def test_query_db_readonly_enforcement():
    """只读工具：非 SELECT / 多语句拒绝。"""
    p = make_platform()
    from capstone.tools import ToolHost

    h = ToolHost(p, make_users()["it_alice"])
    with pytest.raises(Exception, match="只读"):
        h.query_db("DROP TABLE asset")
    with pytest.raises(Exception, match="多语句"):
        h.query_db("SELECT * FROM asset; DELETE FROM request")
    rows = h.query_db("SELECT * FROM asset")
    assert "A-1001" in rows


def test_query_db_unknown_table_errors():
    from capstone.tools import ToolHost

    p = make_platform()
    h = ToolHost(p, make_users()["it_alice"])
    with pytest.raises(ValueError, match="未知表"):
        h.query_db("SELECT * FROM secrets")


def test_submit_request_returns_pending_not_effect():
    """submit_request 只挂起不执行（写路径两阶段的第一阶段）。"""
    p = make_platform()
    from capstone.tools import ToolHost

    h = ToolHost(p, make_users()["it_alice"])
    out = h.submit_request("software_install", "安装 IDE")
    assert '"status": "pending_approval"' in out
    assert p.writes == []
