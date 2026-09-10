"""Ch29 pipeline tests (mock only): 七环 trace、拒答路径、引用输出、冻结检索。"""

from __future__ import annotations

import math

from rag_pipeline.client import Completion
from rag_pipeline.generation import REFUSAL_TEXT
from rag_pipeline.pipeline import RING_STAGES, RagConfig, RagPipeline

VOCAB = ["退款", "换货", "发票", "续费", "价保", "优惠券", "手机号", "闪退", "上传", "权限", "手表", "试用"]


def toy_embed_fn():
    def embed(texts: list[str]) -> list[list[float]]:
        vecs = []
        for t in texts:
            v = [1.0 if w in t else 0.0 for w in VOCAB]
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vecs.append([x / norm for x in v])
        return vecs

    return embed


class FakeLLM:
    def __init__(self, reply: str = "签收后 7 天内可申请退款，1-3 个工作日原路退回 [1]。"):
        self.reply = reply
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512) -> Completion:
        self.calls.append(messages)
        return Completion(text=self.reply, finish_reason="stop", prompt_tokens=10, completion_tokens=5)


def make_pipeline(reply: str = "签收后 7 天内可申请退款，1-3 个工作日原路退回 [1]。") -> tuple[RagPipeline, FakeLLM]:
    llm = FakeLLM(reply)
    return RagPipeline(embed_fn=toy_embed_fn(), llm=llm), llm


def test_trace_records_all_seven_rings_in_order():
    pipe, llm = make_pipeline()
    result = pipe.answer("怎么申请退款")
    stages = [t.stage for t in result.trace]
    assert stages == RING_STAGES  # parsing→cleaning→chunking→metadata→indexing→retrieval→generation
    assert [t.ring for t in result.trace] == list(range(1, 8))
    assert result.answer.refused is False
    assert llm.calls, "generation ring should call the LLM"


def test_refusal_path_when_no_relevant_chunk():
    pipe, llm = make_pipeline()
    result = pipe.answer("竞品X的价格是多少")  # 语料中无答案
    assert result.answer.refused is True
    assert "未找到可靠来源" in result.answer.text
    assert result.answer.refused_reason is not None and "< threshold" in result.answer.refused_reason
    assert llm.calls == []  # 拒答不调用 LLM
    assert [t.stage for t in result.trace] == RING_STAGES  # 拒答也走完七环 trace


def test_answer_carries_citations_from_retrieval_metadata():
    pipe, llm = make_pipeline()
    result = pipe.answer("怎么申请退款")
    a = result.answer
    assert a.citations, "answer text cites [1]"
    c = a.citations[0]
    assert c.chunk_id.startswith("refund:")
    assert c.source == "kb_refund_policy.md"
    assert c.section  # 引用出处来自元数据环，不是模型拼的


def test_context_render_includes_numbering_source_and_framework():
    from rag_pipeline.generation import render_context
    from rag_pipeline.retrieval import retrieve

    pipe, _ = make_pipeline()
    hits = retrieve("怎么申请退款", pipe.index, toy_embed_fn()(["怎么申请退款"])[0], top_k=2)
    ctx = render_context(hits)
    assert "[1] 来源：" in ctx and "章节：" in ctx and "日期：" in ctx
    messages = llm_messages(pipe)
    assert "可能与问题不完全匹配" in messages[0]["content"]  # 框架声明（防确证幻觉，system）


def llm_messages(pipe: RagPipeline) -> list[dict[str, str]]:
    pipe.answer("怎么申请退款")
    return pipe.llm.calls[0]  # type: ignore[union-attr,index]


def test_frozen_retrieval_for_generation_eval():
    """管道原则：评测生成时冻结检索（固定块），不需要真实检索。"""
    pipe, llm = make_pipeline(reply="优惠券每单限用一张，不与积分抵扣叠加 [1]。")
    from rag_pipeline.retrieval import retrieve

    hits = retrieve("优惠券能和积分一起用吗", pipe.index, toy_embed_fn()(["优惠券能和积分一起用吗"])[0], top_k=1)
    result = pipe.answer_with_frozen_hits("优惠券能和积分一起用吗", hits)
    assert result.answer.citations[0].source == "kb_coupon_rules.md"
    assert "优惠券" in llm.calls[0][1]["content"]
    assert [t.stage for t in result.trace] == ["generation"]  # 只评生成环


def test_rag_answer_skeleton_entrypoint():
    pipe, llm = make_pipeline()
    from rag_pipeline.pipeline import rag_answer

    answer = rag_answer("会员自动续费扣款了但已取消订阅，怎么退款？", toy_embed_fn(), llm)
    assert answer.refused is False
    assert "[1]" in answer.text
