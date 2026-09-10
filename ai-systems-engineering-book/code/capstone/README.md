# capstone（Ch60 毕业项目：生产级 AI Agent 平台骨架）

> **Status: DONE**（任务 A：内部知识助手——RAG + 权限 + 审计；29 mock 测试 + 32 条分层评测 + live 冒烟；见 LAST_TESTED.md）

## 1. 目标

全书终点项目：**不写新机制，只做组装与扩展**——把已验证的章节代码接成一次完整任务链路：

```text
ch11 网关（tier 路由/回退/retry） ─┐
ch08/19 手写 Agent Loop（加审批位）─┼→ KnowledgePlatform（组装层）
ch29 七环 RAG（语料换 capstone 域）─┤     ├ security.py   能力约束表 + ACL 检索过滤（ch59）
ch33 Job 化 + 降级矩阵（Ch35）      ─┤     ├ audit.py      审计链（Ch36/59，可回放）
evals-shared-eval-runner（Ch13/17）─┘     └ cost.py       cost per task（Ch40）
```

任务 A（内部知识助手）的三条红线：

1. **写操作工具未经 L1 审批绝不执行**——结构保证：`submit_request` 只挂起请求，写副作用唯一入口在 `ApprovalGate.decide(approve=True)` 路径（`tools.py`）；
2. **检索 ACL fail-closed**——无 ACL 的块宁可检索不到（默认拒绝）；过滤在检索层做，context 不可撤回（ch59 红线）；索引启动前做入库门禁（缺 ACL 文档拒绝启动）；
3. **一次任务的审计链可完整回放**——谁/何时/问什么（哈希脱敏）/检索块（含被拒）/工具调用/审批决定/成本；写路径任务审计不完整拒绝出平台（`AuditRecord.require_complete` 门禁）。

## 2. 目录

```text
src/capstone/
├── platform.py     # 组装层：语料换域（7 篇 IT 知识库，3 密级）+ answer / run_task / Job 化 / 降级矩阵
├── tools.py        # search_docs（只读，复用 ch29 检索+ACL）/ query_db（只读 mock，SELECT-only）/ submit_request（写→L1 审批）
├── security.py     # AccessRule/UserContext（ch59 Minimal 吸收）+ acl_filter + CapabilityTable
├── audit.py        # AuditRecord（require_complete 门禁）+ AuditLog（write/replay）
└── cost.py         # CostLedger：token × tier 价格表 → cost per task
tests/              # 29 个 mock 测试（conftest 注入跨项目 PYTHONPATH）
evals/              # dataset.jsonl（32 条：simple_fact/multi_hop/refuse/permission/sql）+ run_evals.py
examples/smoke.py   # live 冒烟：RAG 问答 → ACL 拒绝 → 写路径审批 → 审计回放 → 成本报表
```

复用清单（PYTHONPATH 跨项目引用，各项目零改动）：`ch08-tool-calling`（ToolRegistry）、`ch11-model-gateway`（Gateway/Router/Tier/FakeProvider）、`ch19-agent-loop`（AgentLoop）、`ch29-rag`（RagPipeline/retrieve/generate/OllamaClient/OllamaEmbedder）、`ch33-ai-backend`（Job/JobQueue/EventStream/transition）、`evals-shared-eval-runner`（run_eval/dataset/metrics）。

## 3. 安装与运行

```bash
cd code/capstone
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e . pytest

# 测试（29 个，全 mock，不依赖 Ollama）
.venv/bin/python -m pytest -q

# 分层评测（mock 模式：检索/权限/SQL/拒答为确定性组件评测；生成质量需 live）
PYTHONPATH=src:../ch08-tool-calling/src:../ch11-model-gateway/src:../ch19-agent-loop/src:../ch29-rag/src:../ch33-ai-backend/src:../evals-shared-eval-runner/src \
  .venv/bin/python evals/run_evals.py

# live 冒烟（需本机 Ollama：bge-m3 + qwen3.5:9b-mlx）
PYTHONPATH=src:../ch08-tool-calling/src:../ch11-model-gateway/src:../ch19-agent-loop/src:../ch29-rag/src:../ch33-ai-backend/src \
  .venv/bin/python examples/smoke.py
```

配置见 `.env.example`（OLLAMA_BASE / LLM_MODEL / EMBED_MODEL；云端供应商只改 LLM_* 三变量，代码零改动）。

## 4. 预期结果（Last verified: 2026-09-10）

- 测试：29 passed（ACL fail-closed×4 + 能力约束×2 / 审批红线双断言 / 只读工具×3 / 审计完整与回放×5 / 成本记账×3 / 降级触发与降级矩阵×2 / 拒答与 ACL 集成×3 / Job 化状态机 / 全链路 mock 冒烟）
- 评测（mock 模式）：32 条 5 层全过——simple_fact 8 / multi_hop 4 / refuse 5 / permission 6 / sql 9；落盘 `results/mock-latest/`（results.jsonl + metadata.json，mode=mock 如实标注）
- live 冒烟（bge-m3 + qwen3.5:9b-mlx，temp 0）：
  - ① 问答：`kb_software_install.md` 引用回答，cost=0.002332（457+42 tokens，standard tier）
  - ② ACL：员工问薪酬 → `salary/server_ops/expense` 被拒（检索层滤除），模型回答"未找到"——**密级内容零泄漏**
  - ③ 写路径：loop 检索→`submit_request` 挂起（副作用 0 条）→未审批执行被显式拒绝→it-manager 批准→ticket T-0001 落地
  - ④ 审计回放完整（谁/哈希/检索块/工具/审批/成本），写任务 cost=0.017192，平台累计 0.020616

## 5. 设计要点（正文对应）

- **红线是结构性的**：写副作用只存在于 `_apply_write`，只有 `ApprovalGate.decide(approve=True)` 能触达——测试断言"未审批→store 空 + 显式拒绝；批准后→副作用 + 审计"（Ch60 Failure Case 二的直接反例）
- **幂等审批**：同一 (user, type, payload) 哈希为同一 request_id——模型重试安全（ch33 幂等提交的应用）
- **降级可见**：模型链耗尽 → ch33 状态机入队（`degraded_job_queued`）+ degraded 事件，绝不假装成功（Ch35 矩阵 queue_later 行）；回退层成功 → degraded 标记贯穿到审计
- **成本口径**：本地部署价格近似 0，价格表为示例（云端演示路由决策）；稳定口径是"每任务几次调用、多少 token、哪个 tier"（Ch40）
- **评测先行分层**（Ch13）：检索/权限/SQL/拒答层可确定性评测（mock 100% 可复现），生成质量层标注需 live——mock 模式的边界如实记录
- **已知边界**：loop 协议依赖模型输出 JSON（qwen3.5:9b 实测两轮内收敛；畸形输出由 ch19 有界恢复兜底）；生产版需把 BM25+本地 embedding 换向量库（七环接口不变）、审计落 append-only 存储、Job 队列换 Redis/MQ

## 6. 迁移检验（Ch60 终问）

换模型/框架/业务时**不动**的部分：ToolRegistry 协议、Gateway provider 抽象、七环管道接口、ACL fail-closed 语义、审批两阶段结构、审计 schema、成本记账口径——**这些是本骨架带走的资产**。
