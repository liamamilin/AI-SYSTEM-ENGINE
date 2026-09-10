# ch11-model-gateway

> **Status: DONE**（实现完成，已实际运行验证；见 LAST_TESTED.md）

## 1. 目标

统一模型调用入口：Provider 抽象（本地 Ollama / OpenAI-compatible 云端）、路由（质量/成本/隐私约束）、回退链（带 degraded 标记）、重试（Ch10 可靠性层）、metrics 落盘（Ch36 雏形）。

## 2. 架构

```text
调用方 → Gateway.complete(messages, constraints)
       → Router.route（按约束排序候选层 = 回退链）
       → 每层: call_with_retry（分类重试）→ 成功即返回
       → 失败则下一层，成功层 i>0 时标记 degraded=True（静默降级禁止）
       → 每次尝试写 metrics.jsonl（tier/model/ok/latency/tokens/degraded）
```

## 3. 目录

```text
src/model_gateway/
├── base.py            # Completion + LLMClient 协议 + Ollama/OpenAICompat/Fake 三个 Provider
├── router.py          # Tier(质量/成本/隐私) + 约束路由
├── retry.py           # RetryPolicy(退避+抖动) + call_with_retry + 类型化错误
└── gateway.py         # 组装：路由→重试→回退(标记)→metrics
configs/gateway.toml   # TODO: 层配置文件化（当前用代码构造）
tests/test_gateway.py  # 11 个 mock 测试
```

## 4. 安装与运行

```bash
cd code/ch11-model-gateway
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e . pytest openai httpx
.venv/bin/python -m pytest -q          # 11 passed
# live 冒烟（本地 Ollama）：
.venv/bin/python -c "..."   # 见正文 Hands-on；构造 Gateway→complete
```

## 5. 预期结果（Last verified: 2026-09-09）

- 测试：11 passed（路由排序/隐私约束/重试成功/上限放弃/不可重试快速失败/回退标记/无回退不标记/metrics 写入/全层宕机抛错）
- live：cloud 层构造性宕机 → 回退 local-9b 真实回答，`degraded=True`，metrics 记录 2 条（[False, True]）

## 6. 设计要点（正文对应）

- **回退必须可见**：`degraded` 标记是本项目第一设计约束
- **重试按类型分流**：NonRetryableError 快速失败（测试证明不浪费）
- **隐私约束硬边界**：`privacy_local_only` 无可用层直接 ValueError，不静默走云
- metrics 是 Ch36 的种子：ts/tier/model/ok/latency/tokens/degraded
