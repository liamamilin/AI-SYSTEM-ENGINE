"""Ch60 capstone — live 冒烟（本机 Ollama：qwen3.5:9b-mlx + bge-m3）。

一次真实 query 走完整链路：
  1. RAG 问答（检索 → 回答 → 引用 → 审计 → 成本）
  2. ACL 拒绝路径（员工问薪酬 → 密级块检索层滤除 → 拒答）
  3. Agent 写路径（loop 检索 → submit_request 挂起 → 未经审批拒绝 → L1 批准 → 执行）
  4. 审计回放 + 成本报表

运行：PYTHONPATH=src:../ch08-tool-calling/src:../ch11-model-gateway/src:../ch19-agent-loop/src:../ch29-rag/src:../ch33-ai-backend/src .venv/bin/python examples/smoke.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_CODE = os.path.dirname(_ROOT)
for p in (
    os.path.join(_ROOT, "src"),
    os.path.join(_CODE, "ch08-tool-calling", "src"),
    os.path.join(_CODE, "ch11-model-gateway", "src"),
    os.path.join(_CODE, "ch19-agent-loop", "src"),
    os.path.join(_CODE, "ch29-rag", "src"),
    os.path.join(_CODE, "ch33-ai-backend", "src"),
):
    if p not in sys.path:
        sys.path.insert(0, p)

from capstone.platform import GatewayLoopClient, KnowledgePlatform  # noqa: E402
from capstone.security import UserContext  # noqa: E402
from capstone.tools import ApprovalRequiredError  # noqa: E402

from model_gateway.base import OllamaProvider  # noqa: E402
from model_gateway.gateway import Gateway, GatewayConfig  # noqa: E402
from model_gateway.router import Router, Tier  # noqa: E402

from rag_pipeline.client import OllamaClient, OllamaEmbedder  # noqa: E402


def main() -> None:
    alice = UserContext(user_id="u001", clearance="internal", departments={"it"}, role="employee")

    # 组装：ch29 七环（语料换 capstone 域）+ ch11 网关（本地 privacy 硬约束）
    embedder = OllamaEmbedder()
    gateway = Gateway(GatewayConfig(router=Router([
        Tier("standard", OllamaProvider(model=os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")),
             "standard", 0.0, "local"),
    ])))
    platform = KnowledgePlatform(
        embed_fn=embedder.embed,
        llm=OllamaClient(),
        gateway=gateway,
    )

    print("=" * 72)
    print("① RAG 问答：检索 → 回答 → 引用 → 审计 → 成本")
    out1 = platform.answer(alice, "非白名单软件怎么申请安装？")
    print(f"  回答: {out1.answer[:120]}...")
    print(f"  引用: {[c['source'] for c in out1.citations]}")
    print(f"  成本: {out1.cost}")

    print("=" * 72)
    print("② ACL 拒绝路径：员工问薪酬（confidential·HR 专属）")
    out2 = platform.answer(alice, "P4 薪级带宽和调薪窗口是多少？")
    print(f"  被拒块: {out2.audit.denied_doc_ids}  允许块: {out2.audit.retrieved_doc_ids}")
    print(f"  拒答: {out2.refused}  → {out2.answer[:60]}...")

    print("=" * 72)
    print("③ Agent 写路径：检索 → submit_request（挂起）→ 未经审批拒绝 → L1 批准 → 执行")
    out3 = platform.run_task(
        alice, "为公司采购一台显示器并提交采购申请", "请先检索采购流程，再帮我提交采购申请",
    )
    print(f"  loop: stop={out3.stop}  answer={out3.answer}")
    print(f"  工具调用: {[(t['tool'], t['ok']) for t in out3.audit.tool_calls]}")
    rid = out3.pending_requests[0]
    print(f"  挂起请求: {rid}（status=pending_approval，写副作用={len(platform.writes)} 条）")
    try:
        platform.raise_if_not_approved(rid)
    except ApprovalRequiredError as e:
        print(f"  红线演示 → 未经审批执行被拒绝: {e}")
    decision = platform.approve(out3.task_id, rid, "it-manager", approve=True)
    print(f"  L1 审批通过 → {decision}")
    print(f"  写副作用落地: {platform.writes}")

    print("=" * 72)
    print("④ 审计回放（写路径任务的完整审计链）+ 成本报表")
    print(out3.audit.replay())
    print(f"  平台累计: {platform.ledger.total()}")
    print("=" * 72)


if __name__ == "__main__":
    main()
