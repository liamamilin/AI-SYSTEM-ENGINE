# Book Content Blueprint

> 本文件由 `../ai_systems_engineering_book_agent_pack/TOC.md` 转换而来，是 Quarto 写作蓝图。
> 源规范以 agent pack 为准；本文件如需修改，必须同步记录到 CHANGELOG.md。

## Book Metadata

- title: AI Systems Engineering
- subtitle: 从 LLM 到 Agent、Serving 与 Post-training
- english_subtitle: Building Reliable, Evaluated and Production-Ready AI Systems
- author: TODO
- book_type: technical（面向软件工程师的教材）
- target_reader: 具备 Python / 基础数据结构 / 数据库 / Web 后端 / Linux-Docker 经验的软件工程师
- core_goal: 把一个 LLM 从“会生成文本的模型”变成可靠、可控、可评测、可部署、可维护、可迭代的真实 AI 系统
- writing_style: 先问题后技术；从最小系统演化；先稳定抽象后具体工具；心智模型优先
- llm_environment: 默认 OpenAI-compatible endpoint（本地 Ollama：qwen3.5:9b / qwen3.8:27b-mlx；云端可选）；Serving/Post-training 章节标注 GPU 需求（租用 24GB 级 NVIDIA GPU）与 MLX 替代路线

---

# Part 0 — AI Systems Engineering Foundations

## Chapter 1 — AI 技术栈与 L4-L6 定位

- goal: 建立 L0-L6 技术栈全景，明确本书聚焦 L4-L6，区分 Research 与 Engineering 视角
- reader_problem: 面对“学 AI”的海量内容不知道该学什么；分不清模型研究和把模型做成系统之间的差别
- key_concepts: L0-L6 技术栈、Research vs Engineering、Model vs System
- expected_output: 一张全书导航地图 + 判断某个问题属于哪一层的决策规则
- notes: 不展开 L0-L3 细节，只讲理解 L4-L6 所必需的最少知识

## Chapter 2 — AI System 的基本组成

- goal: 建立 AI System 的组件分解模型，让读者看到“模型只是系统的一部分”
- reader_problem: 以为“接上 LLM API 就是一个 AI 应用”，结果上线即失败
- key_concepts: Model、Context、Tool、State、Runtime、Backend、Eval、Data、Infrastructure
- expected_output: `AI System = Problem Framing + Model + Context + Tools + State + Runtime + Backend + Data + Evaluation + Reliability + Security + Serving + Economics` 结构图
- notes: 本章是全书核心抽象总览，后续所有 Part 对应其中组件

## Chapter 3 — Problem Framing

- goal: 学会判断业务问题是否需要 LLM、需要哪种形态
- reader_problem: 拿到一个需求不知道该写普通程序还是上模型；用 LLM 解决了本该用规则解决的问题
- key_concepts: 业务问题建模、LLM 是否必要、Deterministic vs Probabilistic、Failure Cost、Requirements/Constraints
- expected_output: Problem Framing 决策流程（含 Failure Cost 矩阵）
- notes: 全书第一个“决策模型”型章节

## Chapter 4 — Workflow vs Agent

- goal: 建立控制权连续谱（普通程序 → Workflow → LLM-enhanced Workflow → Agent），学会划定 Autonomy Boundary
- reader_problem: 什么都要上 Agent；或反过来，明明需要自主性却用死板的 Workflow
- key_concepts: 普通程序、Workflow、LLM-enhanced Workflow、Agent、Autonomy Boundary
- expected_output: 技术选型连续谱 + “什么时候不应该使用 Agent”清单
- notes: 为 Part 3 Agent 章节埋下伏笔

---

# Part 1 — LLM Interface Engineering

## Chapter 5 — LLM 请求的工程模型

- goal: 把一次 LLM 调用拆解为工程对象（Token / Messages / Sampling / Context Window），建立“调用即系统边界”的观念
- reader_problem: 只会调 `chat.completions.create`，不理解参数与失败来源的关系
- key_concepts: Token、Context Window、Messages、Sampling（temperature/top_p）、Reasoning、Model capabilities
- expected_output: LLM 请求的完整工程模型图 + 参数-效果-成本因果链
- notes: Part 1 的地基，所有后续接口工程都基于此模型

## Chapter 6 — Instruction & Prompt Engineering

- goal: 把 Prompt 从“技巧”升级为“Instruction Hierarchy + Context 工程”的工程实践
- reader_problem: Prompt 时好时坏，改一句坏一片，无法系统地调试
- key_concepts: Instruction hierarchy、Examples（few-shot）、Prompt templates、Prompt as Context、Prompt limitations
- expected_output: Prompt 模板结构规范 + Prompt 失效定位方法
- notes: 明确 Prompt Engineering 是 Context Engineering 的子集

## Chapter 7 — Structured Output

- goal: 用 JSON Schema / Pydantic 让 LLM 输出可靠地接入传统软件系统
- reader_problem: LLM 输出的 JSON 偶尔坏掉，程序随机崩溃，不知道如何系统性解决
- key_concepts: JSON Schema、Pydantic、Validation、Constrained output、Retry and repair
- expected_output: 可运行项目 `code/ch07-structured-output/`（minimal + production）
- notes: 第一批正式代码项目之一；含 schema 校验失败的真实 case

## Chapter 8 — Tool Calling

- goal: 理解 Tool Calling 的完整机制（schema、选择、参数、结果回注），建立“模型提议、宿主执行”的边界
- reader_problem: 以为模型“会执行”工具；工具调用参数错误时无从排查
- key_concepts: Tool schema、Tool selection、Arguments、Tool result、Deterministic execution
- expected_output: 可运行项目 `code/ch08-tool-calling/`
- notes: Part 3 Agent 的直接前置

## Chapter 9 — Streaming, Async and Concurrency

- goal: 掌握流式输出与异步并发的工程处理，理解 TTFT 的用户体验意义
- reader_problem: 同步调用打满线程；流式输出不知道怎么处理取消和背压
- key_concepts: Streaming、Async/await、Cancellation、Backpressure、TTFT
- expected_output: async 并发调用的最小实现 + 取消/背压处理规则
- notes: Python asyncio 基础可参考 Appendix A

## Chapter 10 — Reliability of Model Calls

- goal: 为模型调用建立可靠性层（Retry/Backoff/Timeout/Rate limit/Invalid output/Fallback）
- reader_problem: API 偶发 429/超时/坏输出导致线上事故
- key_concepts: Retry、Backoff、Timeout、Rate limit、Invalid output、Fallback
- expected_output: 可靠性层决策表 + 每种失败模式对应的处理规则
- notes: 与 Ch35 Reliability Engineering 区分：本章聚焦单次调用层，Ch35 聚焦系统层

## Chapter 11 — Model Gateway and Routing

- goal: 设计多模型网关：Provider 抽象、模型选择、fallback、质量/延迟/成本权衡
- reader_problem: 多个模型/供应商硬编码散落各处；换模型要改所有代码
- key_concepts: Provider abstraction、Model selection、Fallback、Quality/Latency/Cost、Local vs API models
- expected_output: 可运行项目 `code/ch11-model-gateway/`
- notes: 第一批正式代码项目之一；本地 Ollama 与云 API 统一为 OpenAI-compatible 抽象

---

# Part 2 — Evaluation & Experiment Engineering

## Chapter 12 — Why Eval Is Core Engineering

- goal: 建立 Build-Measure-Diagnose 循环，把 Eval 变成改任何东西之前的习惯
- reader_problem: 每次改 prompt/换模型像赌博；不知道变好还是变坏
- key_concepts: Build-Measure-Diagnose、Baseline、Regression
- expected_output: Eval 优先工作流 + 无 Eval 时系统的实际风险清单
- notes: Part 2 总起章

## Chapter 13 — Eval Dataset Engineering

- goal: 学会构造小型但真实的评测集（case 设计、ground truth、难度分层、元数据、版本化）
- reader_problem: 拿不到大数据集；不知道十几条 case 怎么设计才有代表性
- key_concepts: Case design、Ground truth、Difficulty、Metadata、Versioning
- expected_output: eval dataset 的 JSONL 规范 + 最小样例集
- notes: 数据可由本地模型生成 + 人工审核

## Chapter 14 — Component Evaluation

- goal: 对系统组件（结构化输出/工具选择/工具参数/检索/规划）分别评测
- reader_problem: 系统整体错，不知道哪一层错了
- key_concepts: Structured output eval、Tool choice eval、Tool arguments eval、Retrieval eval、Planning eval
- expected_output: 组件级失败定位表（Failure Model）
- notes: 可运行项目 `code/evals-shared-eval-runner/` 在此投入使用

## Chapter 15 — System Evaluation

- goal: 从任务成功、准确率、延迟、成本、失败率五个维度评测整个系统
- reader_problem: 组件都“挺好”但整体业务不可用
- key_concepts: Task success、Accuracy、Latency、Cost、Failure rate
- expected_output: 系统 eval 报告模板 + 指标基线表
- notes: 与 Ch36 Observability 的线上指标区分：本章是离线/发布前评测

## Chapter 16 — LLM-as-a-Judge

- goal: 掌握用 LLM 评分的方法与偏差校准
- reader_problem: 没有人力做人工标注，又不敢全信自动评分
- key_concepts: Rubrics、Pairwise、Reference-based、Judge bias、Human calibration
- expected_output: Judge 实验设计 + 已知偏差与校准方法
- notes: 强调 judge 本身也需要 eval

## Chapter 17 — Experiment Reproducibility

- goal: 让每次实验可复现、可对比（模型/prompt/dataset/config 版本 + git commit + tracking）
- reader_problem: 三周前的实验结果现在复现不出来
- key_concepts: Model version、Prompt version、Dataset version、Config version、Git commit、Experiment tracking
- expected_output: 实验记录规范（experiments/experiment_registry.md 模板）
- notes: 为全书后续章节的实验提供统一记录格式

---

# Part 3 — Agent Systems Engineering

## Chapter 18 — What Is an Agent?

- goal: 去神秘化：Agent = Model + Loop + Tools + State；辨析 Agent 神话与真实能力边界
- reader_problem: 被“AGI Agents”宣传误导，无法判断哪些任务真正适合 Agent
- key_concepts: Agent 公式、Agent myths、Autonomy
- expected_output: Agent 结构模型 + 能力边界判断规则
- notes: 全书 Agent 部分的锚点章，回扣 Ch4

## Chapter 19 — Build an Agent Loop From Scratch

- goal: 手写最小 Agent Loop（不依赖框架），处理停止条件与工具结果回注
- reader_problem: 用了框架但不知道框架在干什么；自己写就死循环
- key_concepts: Minimal loop、Stop conditions、Tool result loop
- expected_output: 可运行项目 `code/ch19-agent-loop/`（minimal + production）
- notes: 硬性要求：核心实现不依赖大型 Agent Framework

## Chapter 20 — Tool Runtime

- goal: 工程化工具执行：注册表、schema、执行器、超时、错误处理、幂等性
- reader_problem: 工具执行失败/超时/重复执行破坏状态
- key_concepts: Registry、Schema、Executor、Timeout、Error handling、Idempotency
- expected_output: Tool Runtime 工程规范 + 失败处理矩阵
- notes: Ch8 的工程化升级

## Chapter 21 — State

- goal: 区分并管理四类状态：对话态、任务态、应用态、环境态
- reader_problem: 所有状态都塞进消息列表，上下文爆炸且无法恢复
- key_concepts: Conversation state、Task state、Application state、Environment state
- expected_output: 状态分层模型 + 持久化/恢复规则
- notes: 与 Ch23 Memory、Ch24 Context Management 严格区分边界

## Chapter 22 — Planning

- goal: 理解规划的多种实现（隐式规划/ReAct/Plan-and-execute/任务分解）及失败模式
- reader_problem: Agent 复杂任务规划混乱；不知道何时需要显式计划
- key_concepts: Implicit planning、ReAct、Plan-and-execute、Task decomposition、Planning failure
- expected_output: 规划策略选择规则 + 规划失败定位模型
- notes: 手写 ReAct 循环作为实验

## Chapter 23 — Memory

- goal: 区分工作记忆/对话记忆/语义记忆/情景记忆/用户状态，掌握 Memory = persistence + retrieval + injection
- reader_problem: “长期记忆”做成了全部塞向量库，检索出来一团噪声
- key_concepts: Working memory、Conversation memory、Semantic memory、Episodic memory、User state
- expected_output: Memory 分层模型 + 最小 Memory 实现
- notes: 明确 Memory ≠ State ≠ Context（回扣 KNOWLEDGE_CONTRACT 概念边界）

## Chapter 24 — Context Management

- goal: 上下文的选取、排序、剪枝、摘要、压缩与缓存
- reader_problem: 长任务跑着跑着上下文爆掉或关键信息被挤掉
- key_concepts: Selection、Ordering、Pruning、Summarization、Compression、Caching
- expected_output: Context 管理策略库 + 与 Ch27 的分工说明
- notes: Agent 运行时的上下文管理；Ch27 是全局视角

## Chapter 25 — Human-in-the-loop

- goal: 设计审批、升级、置信度与高风险动作的人类介入机制
- reader_problem: Agent 直接执行了不该执行的破坏性动作
- key_concepts: Approval、Escalation、Confidence、High-risk actions、Autonomy boundary
- expected_output: 权限/审批分级表 + 介入点设计规则
- notes: Autonomy Boundary 的工程落地

## Chapter 26 — Multi-Agent and Sub-Agent

- goal: 掌握 handoff/委托/supervisor/隔离，并明确什么时候多 Agent 是不必要的
- reader_problem: 单 Agent 能解决的事拆成了多 Agent，复杂度爆炸
- key_concepts: Handoff、Delegation、Supervisor、Isolation、When multi-agent is unnecessary
- expected_output: 多 Agent 适用性决策规则 + 最小 supervisor 实现
- notes: 强调“多 Agent 是复杂度，不是能力”

---

# Part 4 — Context, Retrieval, Knowledge and Data

## Chapter 27 — Context Engineering

- goal: 全局视角：上下文的六大来源（指令/对话/工具结果/检索/记忆/环境）与组装规则
- reader_problem: 知道一堆技术（RAG、memory、tools）但不知道它们都是 Context 的子问题
- key_concepts: Instructions、Conversation、Tool results、Retrieval、Memory、Environment
- expected_output: Context 组装决策模型（回答“该注入什么、注入多少、什么顺序”）
- notes: Part 4 总起章，把 Prompt（Ch6）、Retrieval（Ch28-31）、Memory（Ch23）统一到 Context 框架

## Chapter 28 — Retrieval Fundamentals

- goal: 掌握稀疏检索（BM25）、稠密检索（embeddings）与混合检索的原理与适用场景
- reader_problem: 以为 RAG = 调 embedding API + 相似度排序，检索质量差不知原因
- key_concepts: Sparse retrieval、BM25、Dense retrieval、Embeddings、Hybrid search
- expected_output: 检索方法决策规则 + 手写 BM25 与 embedding 检索的最小实现
- notes: 不依赖向量库也能跑的最小版本优先

## Chapter 29 — RAG Pipeline

- goal: 端到端构建 RAG：解析→清洗→分块→元数据→索引→检索→生成
- reader_problem: 管道每一步都照抄教程，但整体效果差，不知道该优化哪一步
- key_concepts: Parsing、Cleaning、Chunking、Metadata、Indexing、Retrieval、Generation
- expected_output: 可运行项目 `code/ch29-rag/`（含每步可独立评测的设计）
- notes: Chunking 策略给出可实验对比的 2-3 种方案

## Chapter 30 — Advanced Retrieval

- goal: 掌握检索增强技术（query rewrite、multi-query、filtering、reranking、层级检索、上下文压缩）及其成本收益
- reader_problem: 基础 RAG 到顶后不知道下一步优化什么
- key_concepts: Query rewrite、Multi-query、Filtering、Reranking、Hierarchical retrieval、Context compression
- expected_output: 优化手段-适用问题-成本对照表
- notes: 每种技术都要回答“它修复的是检索失败的哪一种模式”

## Chapter 31 — Retrieval Evaluation

- goal: 用 Recall@K / Precision@K / MRR / NDCG / 引用正确性 / Faithfulness 评测检索与 RAG
- reader_problem: “感觉检索不准”但说不出差多少、差在哪
- key_concepts: Recall@K、Precision@K、MRR、NDCG、Citation correctness、Faithfulness
- expected_output: 检索评测集 + 跑通的指标计算
- notes: 复用 Ch13 的 dataset 规范与 eval-runner

## Chapter 32 — Data Engineering for AI Systems

- goal: 建立数据全生命周期工程观：来源、清洗、去重、版本、隐私、数据契约
- reader_problem: 数据脏、来源不明、无法追溯，系统坏了查不到原因
- key_concepts: Data lifecycle、Provenance、Cleaning、Deduplication、Versioning、Privacy、Data contracts
- expected_output: 数据契约模板 + 数据质量检查清单
- notes: 贯穿纵轴之一（Data）的收束章

---

# Part 5 — Production AI Engineering

## Chapter 33 — AI Backend Architecture

- goal: 设计 AI 后端整体架构：API、Session、Job、Agent runtime、Model、Database、Streaming events
- reader_problem: 把 Agent 塞进 Web 请求-响应模型，长任务全线崩溃
- key_concepts: API、Session、Job、Agent runtime、Model、Database、Streaming events
- expected_output: AI Backend 参考架构图 + 可运行最小后端
- notes: Part 5 总起章；回扣 Ch9 的 async 基础

## Chapter 34 — Long-running Tasks

- goal: 队列、worker、checkpoint、resume、cancellation 的长任务工程
- reader_problem: 十分钟的任务挂在 HTTP 请求里；重启后一切丢失
- key_concepts: Queue、Worker、Async、Checkpoint、Resume、Cancellation
- expected_output: 可运行项目 `code/ch33-ai-backend/` 扩展（队列+worker+checkpoint）
- notes: Docker compose 提供 app/postgres/worker 三服务模板

## Chapter 35 — Reliability Engineering

- goal: 系统层可靠性：fallback、熔断、幂等、优雅降级（升级 Ch10 的调用层视角）
- reader_problem: 单点超时引发雪崩；降级方案没有事先设计
- key_concepts: Retry（系统视角）、Fallback、Circuit breaker、Timeout、Idempotency、Graceful degradation
- expected_output: 可靠性模式决策表 + 故障注入实验
- notes: 注意与 Ch10 的层次区分，避免重复

## Chapter 36 — Observability

- goal: AI 系统可观测三件套：logs/metrics/traces + token/成本/延迟/工具追踪
- reader_problem: 线上回答质量突变但没有任何线索
- key_concepts: Logs、Metrics、Traces、Tokens、Cost、Latency、Tool traces
- expected_output: 追踪数据 schema + 从 trace 定位失败路径的实战
- notes: 与 Ch15 System Eval 区分：观测是线上持续测量

## Chapter 37 — AI Security

- goal: 系统讲解 prompt injection、间接注入、工具滥用、提权、秘密泄露、数据外泄、不安全执行
- reader_problem: 以为“安全”只是内容审核；不知道 Agent 会泄露数据库密码
- key_concepts: Prompt injection、Indirect injection、Tool abuse、Privilege escalation、Secret leakage、Data exfiltration、Unsafe execution
- expected_output: 威胁模型 + 攻击演示（含间接注入真实 case）+ 防御检查清单
- notes: 与 Ch38 组成安全双章；本章讲威胁，Ch38 讲防御机制

## Chapter 38 — Sandbox and Permission Systems

- goal: 设计信任边界、能力模型、读写分离、审批与秘密隔离
- reader_problem: 给 Agent 的工具权限是全有或全无
- key_concepts: Trust boundaries、Capability design、Read/write separation、Approval、Secret isolation
- expected_output: 权限系统最小实现 + 能力设计规范
- notes: Part 3 Ch25 的机制化升级

## Chapter 39 — MCP and Tool Protocols

- goal: 理解工具协议存在的理由，手写最小 MCP server，理解 client/tools/resources/auth
- reader_problem: MCP 概念满天飞，不知道它解决什么、不解决什么
- key_concepts: Why protocols、Client、Server、Tools、Resources、Authentication、Minimal MCP server
- expected_output: 可运行最小 MCP server + “什么时候该用 MCP”决策规则
- notes: 标注规范版本与验证日期（快速变化内容）

## Chapter 40 — AI Economics

- goal: 建立 cost/request、cost/task、token 用量、缓存、模型路由、价值-成本分析的经济视角
- reader_problem: 系统演示惊艳，账单出来破产
- key_concepts: Cost/request、Cost/task、Token usage、Cache、Model routing、Value vs cost
- expected_output: 成本模型计算表 + 优化手段-效果对照
- notes: 全书第三条纵轴（Economics）的收束章

---

# Part 6 — Model Serving & Inference Engineering

## Chapter 41 — LLM Inference Fundamentals

- goal: 理解推理的物理过程：weights、prefill、decode、KV cache
- reader_problem: 不理解为什么长上下文那么慢/贵；所有 serving 参数都是黑盒
- key_concepts: Weights、Prefill、Decode、KV cache
- expected_output: Prefill/Decode 两阶段因果模型（Context 变长→prefill 成本↑→TTFT↑）
- notes: 进入 L5 层；先在 Mac（MLX/llama.cpp）上实测现象，vLLM 实战在 Ch47

## Chapter 42 — GPU Memory

- goal: 建立 GPU 显存分配模型：weights、KV cache、activations 与 context/concurrency 的关系
- reader_problem: 不知道为什么 OOM；不会估算能跑多大模型/多少并发
- key_concepts: Model weights、KV cache、Activations、Context length、Concurrency
- expected_output: 显存估算公式与计算示例（含 24GB GPU 能跑什么的速查表）
- notes: 标注：本机无 NVIDIA GPU，用公式+租用 GPU 实测验证

## Chapter 43 — Batching and Scheduling

- goal: 理解 static batching、continuous batching 与调度对吞吐的影响
- reader_problem: 不理解为什么 vLLM 吞吐比 naive 推理高一个量级
- key_concepts: Static batching、Continuous batching、Scheduling、Throughput
- expected_output: batching 因果模型 + 吞吐对比实验（GPU 上）
- notes: 实验需要租用 GPU（预算标注）

## Chapter 44 — Inference Metrics

- goal: 掌握 TTFT、TPOT、tokens/s、P50/P95/P99 的定义、测量与解读
- reader_problem: 只看平均值做容量决策，长尾用户全部超时
- key_concepts: TTFT、TPOT、Tokens/s、P50、P95、P99
- expected_output: 指标测量方法 + 分位数解读规则
- notes: 复用 Ch9 的 streaming 客户端做测量

## Chapter 45 — Quantization

- goal: 理解 FP16/BF16/INT8/INT4（AWQ/GPTQ）量化及精度-显存-速度权衡
- reader_problem: 不知道量化后模型还剩多少能力、什么时候不能用
- key_concepts: FP16/BF16、INT8、INT4、AWQ、GPTQ、Trade-offs
- expected_output: 量化方案选择规则 + 同模型多精度对比实验
- notes: Mac 上可用 MLX 量化版先行体验

## Chapter 46 — Advanced Inference

- goal: 前缀缓存、投机解码、张量/流水线/专家并行、KV offloading、P-D 分离的机制与适用条件
- reader_problem: 听过一堆优化名词，不知道各自解决什么瓶颈
- key_concepts: Prefix caching、Speculative decoding、Tensor parallel、Pipeline parallel、Expert parallel、KV offloading、Prefill/decode disaggregation
- expected_output: 优化技术-瓶颈-适用规模对照表
- notes: 概念为主，标注哪些需要多卡才能实验

## Chapter 47 — vLLM as a Serving Case Study

- goal: 实战部署 vLLM：安装、OpenAI-compatible API、配置、benchmark、metrics
- reader_problem: 想自部署开源模型但不知从何下手
- key_concepts: Installation、OpenAI-compatible API、Configuration、Benchmark、Metrics
- expected_output: 可运行项目 `code/ch47-vllm/`（含 GPU 环境要求与预算说明）
- notes: 需要租用 24GB GPU；提供云租用硬件级别建议，不绑定供应商；标注 Last verified 日期

## Chapter 48 — Production Serving

- goal: 生产级 serving：负载均衡、路由、自动扩缩、缓存、故障转移、监控
- reader_problem: 单实例跑通了，但不会做成可运维服务
- key_concepts: Load balancing、Routing、Autoscaling、Caching、Failover、Monitoring
- expected_output: serving 生产架构图 + 运维检查清单
- notes: 与 Ch33-36 的 backend 工程衔接；强调复用前面章节成果

---

# Part 7 — Post-training Engineering

## Chapter 49 — When Should You Train?

- goal: 建立 Prompt vs RAG vs Tool vs Training 的决策树，先做成本收益分析
- reader_problem: 遇到问题就想微调，忽略了更便宜的手段
- key_concepts: Prompt vs RAG vs Tool vs Training、Behavior adaptation、Cost-benefit analysis
- expected_output: 训练决策树 + 反模式清单（如“用微调当知识库”）
- notes: Part 7 总起章；明确微调改变行为而非注入知识

## Chapter 50 — Dataset Engineering for Post-training

- goal: 训练数据的收集、清洗、去重、格式化、质量控制、难度与污染防范
- reader_problem: 拿几百条脏数据就开始训练，loss 下降但效果变差
- key_concepts: Collection、Cleaning、Deduplication、Formatting、Quality、Difficulty、Contamination
- expected_output: 训练数据集规范 + 质量检查清单
- notes: 与 Ch13 Eval Dataset、Ch32 Data Engineering 交叉引用

## Chapter 51 — Supervised Fine-Tuning

- goal: 理解 SFT 的 input/target、loss、训练循环与评测
- reader_problem: 跑通了脚本但不知道每一步在做什么、失败在哪
- key_concepts: Input/target、Loss、Training loop、Eval
- expected_output: 最小 SFT 实验（MLX 本地 small model 或租 GPU）+ 训练诊断方法
- notes: “loss 下降 ≠ 模型变好”必须显式演示

## Chapter 52 — LoRA and QLoRA

- goal: 掌握低秩适配的原理、显存节省机制与训练设置，识别失败模式
- reader_problem: 不知道 rank/alpha 怎么选；QLoRA 训练崩了不会诊断
- key_concepts: Low-rank adaptation、Memory savings、Training setup、Failure cases
- expected_output: 可运行项目 `code/ch52-lora/`（双路线：MLX 本地 / CUDA 云端）
- notes: Mac 48GB 可真实完成 9B 模型 MLX LoRA；QLoRA 标注 24GB GPU 需求

## Chapter 53 — Preference Optimization

- goal: 理解偏好数据与 DPO/RLHF/PPO/GRPO/可验证奖励的机制和适用边界
- reader_problem: 分不清 DPO 和 RLHF，不知道自己该用哪个
- key_concepts: Preference data、DPO、RLHF、PPO、GRPO、Verifiable rewards
- expected_output: 偏好优化方法选择规则 + 心智模型
- notes: 概念与机制为主，实验标注 GPU 需求

## Chapter 54 — Synthetic Data and Distillation

- goal: 掌握 teacher/student 蒸馏、数据生成、过滤与风险
- reader_problem: 生成的训练数据分布单一/含有害输出，模型越训越差
- key_concepts: Teacher/student、Data generation、Filtering、Risks
- expected_output: 蒸馏数据流水线（可用 Ollama 云端模型当 teacher）+ 质量过滤规则
- notes: teacher 可用 gpt-oss:120b-cloud，零 GPU 成本

## Chapter 55 — Post-training Evaluation

- goal: 训后评测：同一评测集的 baseline 对比、回归检测、能力权衡分析
- reader_problem: 只看训练指标，不知道模型在其他能力上退化没有
- key_concepts: Baseline、Same eval set、Regression、Capability trade-offs
- expected_output: 训前训后完整评测报告模板
- notes: 强制使用 Ch13/Ch15/Ch17 的评测与复现基础设施

---

# Part 8 — End-to-End AI System Design

## Chapter 56 — AI System Design Method

- goal: 综合全书组件，给出系统设计方法论：从需求约束到架构/模型/上下文/工具/运行时/评测/安全/经济学
- reader_problem: 学了所有零件，不会组装成系统
- key_concepts: Requirements、Constraints、Architecture、Model、Context、Tools、Runtime、Eval、Security、Economics
- expected_output: AI System Design 文档模板（设计评审用）
- notes: Part 8 总起章；每个后续 case study 都用此模板

## Chapter 57 — Coding Agent Case Study

- goal: 端到端分析 Coding Agent：代码搜索、文件系统、shell、patch、测试、沙箱、git、评测
- reader_problem: 用过 coding agent 但不知道内部如何设计与权衡
- key_concepts: Code search、Filesystem、Shell、Patch、Test、Sandbox、Git、Eval
- expected_output: Coding Agent 架构分析 + 关键设计决策的 trade-off 说明
- notes: 以本书写作过程自身为案例素材之一

## Chapter 58 — Research Agent Case Study

- goal: 端到端分析研究型 Agent：搜索、浏览、阅读、抽取、引用、综合
- reader_problem: 研究型任务幻觉严重、引用不可靠
- key_concepts: Search、Browse、Read、Extract、Cite、Synthesize
- expected_output: Research Agent 架构分析 + 引用正确性评测方案
- notes: 复用 Part 4 检索与引用评测

## Chapter 59 — Enterprise Knowledge Agent

- goal: 企业知识场景：RAG + SQL + 工具 + 认证 + 审计 + 权限的完整集成
- reader_problem: 企业场景的权限、审计、合规需求不知如何与 AI 系统结合
- key_concepts: RAG、SQL、Tools、Auth、Audit、Permissions
- expected_output: 企业知识 Agent 架构分析 + 安全审计清单
- notes: 集成 Ch29/Ch37/Ch38 成果

## Chapter 60 — Capstone: Production AI Agent Platform

- goal: 综合项目：完整架构、可运行仓库、评测套件、部署、可观测、安全、成本分析
- reader_problem: 需要一个能拿出手的完整系统证明能力
- key_concepts: Full architecture、Runnable repository、Eval suite、Deployment、Observability、Security、Cost analysis
- expected_output: 可运行项目 `code/capstone/` + 完整设计文档
- notes: BOOK_SPEC 能力目标 20 的最终验证

---

# Appendix

## Appendix A — Python / Async refresher
- goal: 补齐 Python asyncio、类型注解、工程化基础
- notes: 供 Ch9/Ch33 前阅读

## Appendix B — Docker / Linux refresher
- goal: 补齐容器与 Linux 基础
- notes: 供 Part 5/6 前阅读

## Appendix C — PostgreSQL / pgvector
- goal: 数据库与向量检索基础设施速成
- notes: 供 Ch29/Ch33 前阅读

## Appendix D — GPU basics
- goal: GPU 硬件与 CUDA 生态基础
- notes: 供 Part 6/7 前阅读；含租用 GPU 指南

## Appendix E — Multimodal AI
- goal: 多模态系统概览
- notes: 选读

## Appendix F — Framework comparison
- goal: 主流框架如何映射到本书稳定抽象（不是框架教程）
- notes: 强调框架是实现案例

## Appendix G — Glossary
- goal: 术语表（与 GLOSSARY.md 同步生成）

## Appendix H — Current ecosystem notes
- goal: 生态现状与变化追踪方法
- notes: 强调时效性，标注验证日期
