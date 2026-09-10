# ch33-ai-backend

> **Status: DONE**（17 mock 测试通过 + mock server 冒烟通过；见 LAST_TESTED.md）

## 1. 目标

第 33 章七组件 AI 后端的最小可运行实现（无框架、无外部服务）：API 层 / Session / Job / Agent Runtime / 模型接入 / 存储 / 事件流。核心分水岭——**HTTP 请求只负责提交与查询，不承载执行**；同步快任务直答，长任务 Job 化（状态机 + 队列 + Worker + 轮询查询），并落地 Ch35 降级矩阵的两条模型故障路径。

## 2. 架构

```text
用户 → ApiLayer.handle（API 层：分流 + 幂等提交）
     classify(req) -> sync | job
       sync（毫秒-秒级）→ Gateway.complete → SyncResult(answered)
           └ 全层失败 → 降级矩阵：入队"稍后通知"（degraded 可见）
       job（分钟级）→ Job 实体落存储 → accepted→queued → JobQueue 入队 → 立即返回 job_id
JobQueue → Worker（无状态）→ AgentRuntime.execute
     → 每步：取消检查点（有序撤退）/ 超时检查（deadline）→ Gateway 调模型（Ch11）
     → progress 事件 + 进度写存储 → done|failed|cancelled 终局
EventStream：生命周期事件（accepted/queued/started/done/failed/cancelled/degraded）
     写内存日志，可回放（轮询形态；SSE/WS 是同一事件流的传输层）
```

## 3. 目录

```text
src/ai_backend/
├── api.py            # API 层：classify 分流 + 幂等提交 + 同步直答 + 任务三件套 + 降级接管
├── storage.py        # 存储（MemoryStorage，状态唯一权威）+ Session（SessionManager）
├── jobs.py           # Job 实体 + 状态机（accepted→queued→running→done|failed|cancelled）+ JobQueue
├── runtime.py        # Agent Runtime（分步执行/进度/检查点）+ Worker（无状态执行骨架）
├── degradation.py    # 降级矩阵（Ch35：回退链 degraded / 全层耗尽→排队稍后）
└── events.py         # 事件流（{type: progress|log|result|error, stage, payload, ts}，可回放）
tests/test_backend.py # 17 个 mock 测试（FakeProvider/Gateway，不依赖真实 Ollama）
examples/
├── mock_ollama_server.py  # ThreadingHTTPServer 模拟 Ollama /api/chat（含 /control down 开关）
└── smoke_live.py          # live 冒烟：同步直答 + Job 全生命周期 + 两次降级
```

## 4. 运行

```bash
cd code/ch33-ai-backend
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python pytest pydantic httpx
PYTHONPATH=src:../ch11-model-gateway/src .venv/bin/python -m pytest -q   # 17 passed
# live 冒烟（mock server，无需 Ollama）：
PYTHONPATH=src:../ch11-model-gateway/src .venv/bin/python examples/smoke_live.py
```

模型接入复用 Ch11 网关：`PYTHONPATH` 跨项目引用 `../ch11-model-gateway/src`（Gateway/Router/Tier/RetryPolicy/FakeProvider/OllamaProvider 均不改动）。

## 5. 预期结果（Last verified: 2026-09-10）

- 测试：17 passed（分流规则×3 / 同步直答 / Job 入队 / 全生命周期状态机 / 非法迁移拒绝 / 幂等提交 / 超时→failed / 降级回退 degraded / 全层耗尽→排队降级+诚实失败 / 事件回放与过滤 / 失败事件 / 排队取消 / 运行中取消有序撤退 / 并发排队×6 / 会话归属）
- 冒烟：①quick 同步直答 `answered`（degraded=False）；②长任务 3 步提交即断连，终态 done progress=1.0，事件流 accepted→queued→started→done；③mock server 置 down → 回退层接管，`degraded=True`；④回退链也挂 → `queued_later`（降级矩阵 queue_later）+ 后台 Job 诚实 failed

## 6. 设计要点（正文对应）

- **分流是分水岭**：`classify` 按 kind / est_seconds 阈值（默认 5s）分流；quick 走同步直答，long 一律 Job 化——时间尺度决定接口形态
- **提交即断连**：POST 语义 = 幂等创建 + 入队 + 返回 job_id（排队不是失败）；查询用 get_job 轮询，事件流让等待可见
- **状态机是契约**：非法迁移抛 `InvalidTransitionError`；终局（done/failed/cancelled）不可复活
- **取消 = 有序撤退**：queued 直改终局；running 置标志，Runtime 在检查点之间停止（不杀进程，每步有状态交代）
- **Worker 无状态**：任务态全在 MemoryStorage——水平扩容即加 Worker 实例（案例二的红利）
- **超时必终局**：Job 带 deadline，Runtime 任何异常/超时都落到 failed，绝不挂死、绝不假装成功
- **降级必须可见**：回退链 degraded 标记（Ch11 原则）+ degraded 事件 + queue_later 明示降级（Ch35 矩阵预设计）
- 事件契约：`{type: progress|log|result|error, stage, payload, ts}`——生命周期走 stage，前端按 type 分发
