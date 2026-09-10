"""Shared fixtures: PYTHONPATH wiring + mock platform builders (mock 优先)."""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
_CODE = os.path.dirname(_ROOT)

for p in (
    os.path.join(_ROOT, "src"),
    os.path.join(_CODE, "ch08-tool-calling", "src"),
    os.path.join(_CODE, "ch11-model-gateway", "src"),
    os.path.join(_CODE, "ch19-agent-loop", "src"),
    os.path.join(_CODE, "ch29-rag", "src"),
    os.path.join(_CODE, "ch33-ai-backend", "src"),
    os.path.join(_CODE, "evals-shared-eval-runner", "src"),
):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402

from capstone.platform import (  # noqa: E402
    CAPSTONE_ACL,
    CAPSTONE_DOCS,
    KnowledgePlatform,
    toy_embed_fn,
)
from capstone.security import UserContext  # noqa: E402

from rag_pipeline.client import Completion  # noqa: E402


def J(**kw) -> str:
    return json.dumps(kw, ensure_ascii=False)


class FakeLLM:
    """ch29 协议的 fake 生成端（RAG ring 7 用）。"""

    def __init__(self, reply: str = "根据知识库，非白名单软件需在 ITSM 提交安装申请，IT 审批后 1 个工作日内远程安装 [1]。"):
        self.reply = reply
        self.calls: list[list[dict]] = []

    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512) -> Completion:
        self.calls.append(messages)
        return Completion(text=self.reply, finish_reason="stop", prompt_tokens=10, completion_tokens=5)


class FlakyThenOkLLM:
    """第一次调用抛错（模拟模型故障），之后正常。"""

    def __init__(self, reply: str = "依据片段回答 [1]。"):
        self.reply = reply
        self.calls = 0

    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512) -> Completion:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("fake model down")
        return Completion(text=self.reply, finish_reason="stop", prompt_tokens=10, completion_tokens=5)


class ScriptedClient:
    """ch19 loop 协议的确定性回放 client（同 ch19 tests）。"""

    def __init__(self, outputs: list[str]):
        self.outputs = list(outputs)
        self.calls: list[list[dict]] = []

    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512):
        self.calls.append([dict(m) for m in messages])
        from tool_calling.client import Completion as TCCompletion

        return TCCompletion(
            text=self.outputs.pop(0), finish_reason="stop",
            prompt_tokens=12, completion_tokens=8,
        )


def make_users() -> dict[str, UserContext]:
    return {
        "it_alice": UserContext(user_id="u001", clearance="internal", departments={"it"}, role="employee"),
        "hr_bob": UserContext(user_id="u002", clearance="confidential", departments={"hr"}, role="approver"),
        "guest": UserContext(user_id="u003", clearance="public", departments={"sales"}, role="guest"),
        "finance_carol": UserContext(user_id="u004", clearance="internal", departments={"finance"}, role="employee"),
    }


def make_platform(llm=None, *, gateway=None, docs=None, acl=None) -> KnowledgePlatform:
    return KnowledgePlatform(
        embed_fn=toy_embed_fn(),
        llm=llm or FakeLLM(),
        gateway=gateway,
        docs=docs or CAPSTONE_DOCS,
        acl=acl or CAPSTONE_ACL,
    )


@pytest.fixture
def users() -> dict[str, UserContext]:
    return make_users()


@pytest.fixture
def platform():
    return make_platform()
