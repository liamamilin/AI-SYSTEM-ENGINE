# Part 1 Chapter Plans — LLM Interface Engineering (Ch5–11)

> 内部写作计划。本 Part 的统一实验环境：OpenAI-compatible endpoint（本地 Ollama，`qwen3.5:9b-mlx` 快速验证 / `qwen3.8:27b-mlx` 质量验证）；`base_url` 统一抽象。

---

## Ch5 — LLM 请求的工程模型

**Problem**：工程师会调 `chat.completions.create`，但把 temperature、max_tokens、context window 当玄学：回答不稳定不知为何，长对话突然报错不知因何。参数不是配置项，是系统行为的控制变量。

**Learning objectives**
- 拆解一次请求的全部工程对象：Token、Messages、Context Window、Sampling 参数、Reasoning
- 建立“参数 → 行为 → 成本/延迟”的因果链
- 用 Token 预算模型估算成本与上下文容量

**Concepts**：Token、Context Window、Messages（role/内容结构）、Sampling（temperature/top_p/max_tokens）、Reasoning（思考型模型）、Model capabilities

**Mental model（因果性）**
```text
temperature↑ → 多样性↑ 稳定性↓
context↑ → 费用↑ TTFT↑ 关键信息稀释风险↑
max_tokens 不足 → 截断而非报错 → 下游解析崩溃
消息累积 → 上下文溢出 → 硬错误
```
本地实测：用 Ollama 跑同一 prompt 不同 temperature/长度，观察输出分布与延迟。

**Minimal system**：`ch05` 无独立代码项目；用直连 Ollama 的最小脚本做 4 组对照实验（temperature、上下文长度、max_tokens 截断、system role 行为）。

**Failure cases**
1. max_tokens 默认值太小，输出被截断，JSON 解析偶发崩溃（每 20 次一次，极难排查）
2. 多轮对话无限累积，达到 context 上限，服务端 400
3. temperature=1.0 用于结构化抽取，字段值随机抖动

**Eval**：Token 计数与成本估算练习；参数-效果预测 quiz（先预测后实测）。

**Exercises**：Concept（token/context 辨析）；Coding（写预算守卫：请求前估算 token 超限则拒绝）；Debugging（三个“随机失败”案例归因）。

**Connection**：请求模型中最重要的一块输入是 Instruction——Ch6。

---

## Ch6 — Instruction & Prompt Engineering

**Problem**：Prompt 是大多数团队的“唯一工具”，却被当作文本艺术：时好时坏、改一句坏一片、无人敢动。原因：没有指令层次、没有模板结构、没有版本化——Prompt 需要工程化。

**Learning objectives**
- 建立 Instruction Hierarchy（system > developer > user > 注入内容）
- 用结构化模板组织 Prompt（角色/任务/约束/示例/输出格式）
- 把 few-shot 示例当作“规格说明”来选择
- 知道 Prompt 的能力边界：什么必须交给 Tool/RAG/微调

**Concepts**：Instruction hierarchy、Examples（few-shot）、Prompt templates、Prompt as Context、Prompt limitations

**Mental model（结构性）**
```text
Prompt = 程序（指令 + 约束 + 流程说明）
       + 规格示例（few-shot = 行为规格）
       + 数据（当前输入）
三者分离管理、版本化，而非一段散文
```
决策规则：行为变化 → 改模板并跑 eval；知识缺失 → RAG/Tool；稳定行为不达 → 考虑 Post-training（呼应 Ch49）。

**Minimal system**：把一段“散文 prompt”重构为结构化模板，同一 eval 集（20 条）前后对比。

**Failure cases**
1. 指令写在中段被长输入“淹没”，偶发不遵守（位置敏感）
2. few-shot 示例含真实用户 PII 且被模型复读
3. 冲突指令（system 说拒绝、user 要求绕过）行为不可预测
4. prompt 直接拼用户输入，被注入指令劫持（预告 Ch37）

**Eval**：模板重构前后的同集对比（引用 Ch13 方法，此处先用最简通过/失败标记）。

**Exercises**：Concept（hierarchy 排序练习）；Coding（模板引擎 + 版本号）；Debugging（“改 prompt 引发回归”实验）。

**Connection**：Prompt 能让模型“说出”结构，但不能保证——输出结构需要 Ch7。

---

## Ch7 — Structured Output

**Problem**：LLM 输出的 JSON 有 1%-5% 概率带 markdown 围栏、尾逗号、字段名变异。工程师用 `json.loads` 裸解析，线上随机崩溃。文本到软件的接口必须像 API 一样有契约。

**Learning objectives**
- 用 Pydantic/JSON Schema 定义输出契约
- 理解 constrained decoding 的原理与可用性
- 实现解析失败的重试与修复策略
- 把结构化输出接入传统软件的调用链

**Concepts**：JSON Schema、Pydantic、Validation、Constrained output、Retry and repair

**Mental model（结构性 + 失败性）**
```text
LLM text → Extract → Validate(schema) → 合法? → 业务使用
                                    ↓ 否 → Repair(reprompt/error feedback) → 重验（有限次）
失败定位：字段全错=模型理解问题；偶发格式错=解析问题；特定字段错=schema 描述问题
```

**Minimal system**：`code/ch07-structured-output/minimal/`——单文件：调用 Ollama → 提取 JSON → Pydantic 校验 → 失败打印原因。**运行验证**。

**暴露问题**：故意演示三类失败（围栏包裹、字段缺失、类型漂移），minimal 版本全部崩溃。

**Engineering system**：`production/`——schema 定义与 prompt 同源、error-feedback 重试（上限 2 次）、校验错误回注、metrics（首次成功率/重试率）、pytest（mock + live 可选）、eval 集验证首次解析成功率。

**Failure cases**：围栏包裹率随模型不同；嵌套 schema 深层字段漂移；重试导致成本翻倍但成功率仅 +2%（不值得）。

**Trade-offs**：constrained decoding 可靠但部分端点不支持；error-feedback 重试有效但增加延迟成本。

**Eval**：50 条样例的首次解析成功率 / 重试后成功率 / 各失败类型分布。

**Connection**：结构化输出的最大用途之一是让模型“点菜”——Ch8 Tool Calling。

---

## Ch8 — Tool Calling

**Problem**：模型只知道世界在训练截止前的样子，且不能执行任何动作。要让模型查数据库、发请求、算数，需要一套“模型提议、宿主执行”的机制。工程师常见误解：“模型自己调了工具”。

**Learning objectives**
- 定义完整 Tool：Name/Description/Schema/Executor/Permission/Result
- 实现完整的“提议→校验→执行→回注”循环
- 用 Tool result 回注驱动多轮工具链
- 建立确定性执行的边界意识（模型永不直接执行）

**Concepts**：Tool schema、Tool selection、Arguments、Tool result、Deterministic execution

**Mental model（结构性）**
```text
模型输出: tool_call(name, arguments-json)
宿主: 校验参数(schema) → 检查权限 → 执行(确定性) → 结果回注 messages → 下一轮
误解纠正: 模型是"提案人"，宿主是"执行人"
```

**Minimal system**：`code/ch08-tool-calling/minimal/`——两个工具（get_weather、calculator，后者用真实计算避免模型心算错误）手写循环。**运行验证**。

**暴露问题**：模型编造不存在的工具名；参数类型漂移；工具报错后模型放弃或循环重复调用。

**Engineering system**：`production/`——工具注册表（decorator 自动生成 schema）、参数校验、错误信息结构化回注（教模型自纠）、调用记录。tests：happy path / 不存在工具 / 错误参数 / 工具异常。eval：工具选择正确率、参数正确率（这是 Ch14 组件评测的雏形）。

**Failure cases**
1. 工具描述含糊导致选择错误率 30%（描述质量 = 选择质量）
2. 参数 schema 无 enum 约束，模型自造枚举值
3. 工具报错信息是堆栈原文，模型读不懂，行为恶化

**Trade-offs**：工具越多选择越难（给 Ch24 上下文管理埋伏笔）；native tool calling vs 纯 prompt 模拟的兼容性差异。

**Connection**：单工具调用是同步阻塞的；真实系统需要并发与流式——Ch9。

---

## Ch9 — Streaming, Async and Concurrency

**Problem**：同步调用一个 LLM 要 2-30 秒。Web 服务用同步代码=线程耗尽；批量任务用同步循环=串行龟速；用户看不到任何反馈=体验崩坏。AI 后端必须 async-first。

**Learning objectives**
- 实现 streaming 输出与 TTFT 感知
- 用 asyncio 并发调用（gather/semaphore 控制并发度）
- 处理取消（用户离开）与背压（消费慢于生产）
- 理解 TTFT 对体验的量化意义

**Concepts**：Streaming、Async/await、Cancellation、Backpressure、TTFT

**Mental model（因果性）**
```text
同步 N 个调用 = N × 延迟；async 并发 = max(延迟)（受并发上限约束）
并发度↑ → 吞吐↑ 但触发 rate limit / 服务端排队 → P99 恶化
streaming 不减少总时间，但 TTFT 从秒级降到首 token 时间
```

**Minimal system**：直连 Ollama 的 async 脚本：10 个请求串行 vs 并发 vs 限流并发的耗时对比 + streaming 首 token 计时。**运行验证**（本机实测）。

**暴露问题**：无限并发触发 429；streaming 中途客户端取消，服务端继续计费；asyncio.gather 一个失败全军覆没。

**Engineering system**：信号量限流、逐任务异常隔离（return_exceptions）、cancellation 传播、消费端背压（queue）。（进阶实现并入 Ch10/Ch11 项目。）

**Failure cases**
1. 并发 50 打本地 Ollama，队列排爆，全部超时
2. gather 未隔离异常，一个请求失败整个批处理作废
3. SSE 流被代理缓冲，用户 30 秒后才看到全部内容（TTFT 优化白做）

**Trade-offs**：并发度与 rate limit/延迟长尾的权衡；streaming 增加客户端复杂度。

**Eval**：P50/P95 延迟与吞吐随并发度变化的实测曲线。

**Connection**：并发带来了新的失败面——超时、429、坏输出——需要系统性处理：Ch10。

---

## Ch10 — Reliability of Model Calls

**Problem**：LLM API 是分布式的概率服务：429、超时、瞬时 5xx、格式错误输出是常态而非异常。没有可靠性层的系统“平均每 N 次调用崩一次”，N 大到开发期注意不到，流量一大必然事故。

**Learning objectives**
- 为每类失败（429/超时/5xx/坏输出/内容过滤）匹配正确策略
- 实现指数退避 + 抖动的重试（含不可重试错误识别）
- 设计 fallback 链（模型降级/端点切换）
- 建立调用可靠性度量（重试率、失败率）

**Concepts**：Retry、Backoff（exponential + jitter）、Timeout、Rate limit、Invalid output、Fallback

**Mental model（决策性 + 失败性）**
```text
429/超时/5xx → 可重试：退避重试（有限次）
400/认证/内容过滤 → 不可重试：直接失败或换路径
坏输出 → 重试改参数 or 修复（借 Ch7）
全部失败 → fallback 模型/端点 → 再失败 → 显式失败给上层
铁律：重试必须有上限、必须幂等安全（呼应 Ch20）
```

**Minimal system**：直白重试脚本演示“无抖动的同步重试风暴”（20 个并发同时重试→429 雪崩）。**运行验证**。

**暴露问题**：重试风暴自我放大；无限重试挂死调用方；重试不幂等导致重复副作用。

**Engineering system**：并入 `code/ch11-model-gateway/`（可靠性层是网关的组成部分），含重试策略配置、per-错误类型策略表、指标输出。tests：429 重试、超时、不可重试快速失败、fallback 触发（全部 mock，live 可选）。

**Failure cases**
1. 固定间隔重试 20 并发 → 雪崩放大 10 倍流量
2. 重试了非幂等的“发送邮件”工具调用 → 重复发送（预告 Ch20 幂等性）
3. timeout 设 120s，用户 30s 就放弃了，钱照付

**Trade-offs**：重试提高成功率但放大流量与成本；fallback 模型质量下降需要显式告知或标记。

**Eval**：故障注入（mock 服务随机 429/超时）下的成功率、P99、成本对比（无重试/朴素重试/本方案）。

**Connection**：把重试、超时、fallback、模型选择集中管理的组件，就是模型网关——Ch11。

---

## Ch11 — Model Gateway and Routing

**Problem**：三个月里团队换了三次模型、接了两个供应商，散落各处的客户端代码改了上百处；本地模型和云 API 行为不一致，测试无法稳定复现。模型调用需要统一入口。

**Learning objectives**
- 设计 Provider 抽象（OpenAI-compatible 统一接口）
- 实现基于质量/延迟/成本的模型路由
- 实现 fallback 链与本地/云模型混布
- 把 Ch7-Ch10 的成果（结构化输出/可靠性/async）组装进网关

**Concepts**：Provider abstraction、Model selection、Fallback、Quality/Latency/Cost、Local vs API models

**Mental model（结构性）**
```text
调用方 → Gateway(config: 模型清单+策略)
       → 路由(质量/延迟/成本/隐私约束)
       → Provider(local-ollama | cloud-api)  ← 统一 OpenAI-compatible
       → 可靠性层(Ch10) → 结构化输出层(Ch7)
       → metrics(调用/延迟/token/成本 → Ch36 预告)
```
决策规则：隐私敏感/成本敏感 → 本地；质量关键 → 云端强模型；批量离线 → 便宜模型。

**Minimal system**：`code/ch11-model-gateway/minimal/`——抽象基类 + 两个 Provider（ollama-local、openai-compatible-cloud）+ 配置化选择。**运行验证**（本机 Ollama 实测）。

**暴露问题**：不同端点字段差异（tool calling 支持度、reasoning 字段）；无指标时路由决策全靠感觉；fallback 静默降质无人知晓。

**Engineering system**：`production/`——完整网关：路由策略表、fallback 链（云→本地）、重试/超时配置（Ch10）、结构化输出 helper（Ch7）、调用 metrics（jsonl 记录）、pytest 全 mock 覆盖 + live 开关、README 完整命令、`.env.example`、`LAST_TESTED.md`。**全部实际运行验证**。

**Failure cases**
1. 网关返回统一格式，但把供应商特有错误吞掉，排查无门
2. fallback 到本地小模型，质量下降无标记，评测指标静默恶化
3. 配置里模型名硬编码，供应商改名（model deprecation）全线故障

**Trade-offs**：网关统一性 vs 供应商特性能力的损失；本地模型省成本但运维负担。

**Eval**：路由决策正确性（给定约束选对模型）；fallback 触发率；网关引入的额外延迟 < 5ms。

**Connection**：有了可靠的模型调用层，如何知道“行为对不对”？——Part 2 全部关于测量。先问为什么 Eval 是核心工程：Ch12。
