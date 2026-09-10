"""Security tests: ACL fail-closed + 能力约束表（ch59 Minimal 吸收验证）。"""

from __future__ import annotations

import pytest

from capstone.security import AccessRule, CapabilityTable, PermissionError_, UserContext, acl_filter
from rag_pipeline.retrieval import Hit

from conftest import make_platform, make_users, toy_embed_fn

from rag_pipeline.models import Chunk, ChunkMeta


def _hit(doc_id: str, score: float = 0.9) -> Hit:
    return Hit(
        chunk=Chunk(chunk_id=f"{doc_id}-c0", doc_id=doc_id, text="x",
                    meta=ChunkMeta(source=f"{doc_id}.md", section="s", date="2026-08-01")),
        parent=None, bm25_score=score, dense_score=score, score=score,
    )


RULES = {
    "pub": AccessRule(doc_id="pub", clearance="public", departments=set()),
    "itdoc": AccessRule(doc_id="itdoc", clearance="internal", departments={"it"}),
    "hrdoc": AccessRule(doc_id="hrdoc", clearance="internal", departments={"hr"}),
    "secret": AccessRule(doc_id="secret", clearance="confidential", departments={"it"}),
}


def test_acl_fail_closed_missing_rule_denied():
    """无 ACL 的块 = 拒绝（fail-closed，默认拒绝）。"""
    user = make_users()["it_alice"]
    allowed, denied = acl_filter([_hit("unknown_doc")], user, RULES)
    assert allowed == [] and denied == ["unknown_doc"]


def test_acl_clearance_insufficient_denied():
    """密级不足直接短路拒绝。"""
    user = make_users()["it_alice"]  # internal
    allowed, denied = acl_filter([_hit("secret")], user, RULES)  # confidential
    assert allowed == [] and denied == ["secret"]


def test_acl_department_mismatch_denied():
    """部门不符拒绝（非 public 需部门交集）。"""
    alice = make_users()["it_alice"]
    allowed, denied = acl_filter([_hit("hrdoc")], alice, RULES)
    assert denied == ["hrdoc"]
    hr_bob = UserContext(user_id="u002", clearance="confidential", departments={"hr"})
    allowed, denied = acl_filter([_hit("hrdoc")], hr_bob, RULES)
    assert [h.chunk.doc_id for h in allowed] == ["hrdoc"] and denied == []


def test_acl_public_allows_any_dept():
    """public 全放行（任何部门、任意密级 >= public）。"""
    guest = make_users()["guest"]
    allowed, denied = acl_filter([_hit("pub")], guest, RULES)
    assert [h.chunk.doc_id for h in allowed] == ["pub"] and denied == []


def test_capability_table_denies_guest_write():
    """能力约束：guest 无写工具权限（默认拒绝）。"""
    table = CapabilityTable()
    guest = make_users()["guest"]
    with pytest.raises(PermissionError_):
        table.check(guest, "submit_request")
    table.check(guest, "search_docs")  # 只读工具放行


def test_acl_gate_rejects_index_without_rules():
    """入库门禁：索引里存在无 ACL 文档 → 平台拒绝启动（fail-closed 在 build 时）。"""
    from capstone.platform import CAPSTONE_DOCS
    with pytest.raises(RuntimeError, match="无 ACL 规则"):
        make_platform(docs=CAPSTONE_DOCS, acl={k: v for k, v in make_users_acl_partial().items()})


def make_users_acl_partial():
    from capstone.platform import CAPSTONE_ACL
    return {k: v for k, v in CAPSTONE_ACL.items() if k != "salary"}


def test_platform_search_filters_confidential_for_it_employee():
    """集成：IT 员工检索 → confidential 块被滤除（检索层过滤，context 不可撤回）。"""
    p = make_platform()
    alice = make_users()["it_alice"]
    out = p.search(alice, "薪级带宽和调薪窗口是怎样的？")
    assert "salary" in out.denied_ids
    assert "salary" not in out.allowed_ids
