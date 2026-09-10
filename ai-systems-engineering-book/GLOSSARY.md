# GLOSSARY.md

> 全书稳定术语登记表。核心术语按 KNOWLEDGE_CONTRACT.md 的 YAML 格式维护。
> 规则：新增核心概念前先查本表；禁止 concept drift（同一概念多名 / 同名多义）。
> 修改必须记入 CHANGELOG.md。

## 1. 概念边界（必须遵守）

```text
Prompt ≠ Context
Context ≠ Memory
Memory ≠ State
Tool ≠ Agent
Workflow ≠ Agent
Model ≠ Agent
Agent ≠ AI System
Retrieval ≠ RAG
RAG ≠ Knowledge Base
Fine-tuning ≠ Database
Eval ≠ Benchmark only
Framework ≠ Capability
```

## 2. 核心概念

```yaml
concept:
  name: Model
  chinese_name: 模型
  definition: 执行概率生成/推理的模型本体。模型不是完整 AI 系统。
  why_it_exists: 把语言/推理能力封装为可调用的概率函数
  prerequisites: 无
  mental_model: "Model = f(context) → 概率分布 → 采样输出"
  alternatives: 规则引擎、传统分类模型
  tradeoffs: 通用能力强但输出不确定；能力与成本/延迟正相关
  failure_modes: 幻觉、能力不足、输出格式不稳定
  related_concepts: [Context, Serving, Post-training]
  implementation_examples: Ch5
  evaluation: 组件级评测（Ch14）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Instruction
  chinese_name: 指令
  definition: 告诉模型"应该如何处理当前任务"的上下文信息。Prompt Engineering 属于 Context Engineering 的子集。
  why_it_exists: 模型行为依赖任务说明的质量与层次
  prerequisites: [Model, Context]
  mental_model: "Instruction 是 Context 中具有最高行为约束力的部分"
  alternatives: —
  tradeoffs: 指令越精确行为越稳，但过长会挤占有效上下文
  failure_modes: 指令冲突、指令被注入内容覆盖、指令层级混乱
  related_concepts: [Context, Context Engineering]
  implementation_examples: Ch6
  evaluation: Prompt A/B（Ch13/Ch17）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Context
  chinese_name: 上下文
  definition: 模型在一次推理中能够看到的信息集合。可能包括 instructions、conversation、retrieved information、tool result、memory、environment state、current task state。
  why_it_exists: 模型只能基于输入推理；输入质量决定输出上限
  prerequisites: [Model]
  mental_model: "Context = 有限预算内的信息组合决策"
  alternatives: —
  tradeoffs: 信息越多越全，但成本/延迟上升、关键信息被稀释
  failure_modes: 上下文溢出、关键信息缺失、顺序不当、注入攻击
  related_concepts: [Instruction, Memory, Context Management, Retrieval]
  implementation_examples: Ch5, Ch24, Ch27
  evaluation: 组件级评测（Ch14）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Tool
  chinese_name: 工具
  definition: 由宿主程序提供、可由模型请求调用的确定性或外部能力。通常包含 Name、Description、Schema、Executor、Permission、Result。模型提出 tool call，不等于模型自己直接执行工具。
  why_it_exists: 补齐模型缺乏的实时信息、确定性计算与副作用能力
  prerequisites: [Model, Structured Output]
  mental_model: "模型提议 → 宿主校验 → 宿主执行 → 结果回注"
  alternatives: Fine-tuning 注入知识（不适用于实时/副作用场景）
  tradeoffs: 能力扩展 vs 攻击面扩大与可靠性负担
  failure_modes: 参数错误、执行超时、重复执行、权限滥用
  related_concepts: [Tool Calling, Tool Runtime, MCP, Permission]
  implementation_examples: Ch8, Ch20, Ch39
  evaluation: Tool choice/arguments 评测（Ch14）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: State
  chinese_name: 状态
  definition: 系统在不同执行步骤之间持久化的当前状态。包括 conversation state、task state、application state、environment state。
  why_it_exists: 多步执行需要跨步骤的一致性与可恢复性
  prerequisites: [Agent Runtime]
  mental_model: "State 是系统的数据库视角；Context 是模型的一次性输入视角"
  alternatives: 全部塞进消息列表（反模式）
  tradeoffs: 状态越持久越可恢复，但一致性与清理成本越高
  failure_modes: 状态膨胀、不一致、丢失（崩溃后无法恢复）
  related_concepts: [Memory, Context, Agent Runtime]
  implementation_examples: Ch21
  evaluation: 状态转换测试（CODE_STANDARD §5）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Memory
  chinese_name: 记忆
  definition: 能够跨当前短期上下文保存、检索和重新注入信息的机制。通常建立在 persistence + retrieval + context injection 之上。
  why_it_exists: 上下文窗口有限且昂贵；重要信息需要跨会话存活
  prerequisites: [Context, State, Retrieval]
  mental_model: "Memory = persistence + retrieval + injection"
  alternatives: 长上下文模型（成本更高）、外部数据库直查
  tradeoffs: 记得越多越智能，但检索噪声与成本越高
  failure_modes: 检索噪声、过时信息污染、隐私泄露
  related_concepts: [State, Context, Retrieval]
  implementation_examples: Ch23
  evaluation: 检索正确性评测（Ch31）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Workflow
  chinese_name: 工作流
  definition: 预先定义控制流的任务执行流程。控制权主要由程序决定。
  why_it_exists: 确定性步骤不应交给模型决定
  prerequisites: —
  mental_model: "控制权连续谱：程序 → Workflow → LLM-enhanced Workflow → Agent"
  alternatives: Agent（控制权交给模型）
  tradeoffs: 可靠可测 vs 灵活性不足
  failure_modes: 分支爆炸、无法适应新情况
  related_concepts: [Agent, LLM-enhanced Workflow]
  implementation_examples: Ch4
  evaluation: 系统评测（Ch15）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Agent
  chinese_name: 智能体
  definition: 能够基于模型输出动态选择下一步动作的运行系统。简化模型：Agent = Model + Loop + Tools + State。Production Agent 还需要 context management、permissions、reliability、tracing、evaluation。
  why_it_exists: 开放性任务无法预定义全部控制流
  prerequisites: [Model, Tool, State]
  mental_model: "Agent = Model + Loop + Tools + State"
  alternatives: Workflow（可预定义控制流时优先）
  tradeoffs: 灵活性 vs 可预测性/安全性/成本
  failure_modes: 死循环、规划失败、权限滥用、成本失控
  related_concepts: [Agent Runtime, Workflow, Autonomy]
  implementation_examples: Ch19
  evaluation: 任务成功率（Ch15）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Agent Runtime / Harness
  chinese_name: 智能体运行时
  definition: 负责组织模型、工具、状态、上下文和执行循环的宿主系统。
  why_it_exists: Agent 的可靠运行需要循环之外的工程设施
  prerequisites: [Agent, Tool Runtime, State]
  mental_model: "Runtime 是 Agent 的操作系统"
  alternatives: 框架内置 runtime（LangGraph / Agents SDK 等）
  tradeoffs: 自建可控 vs 框架省力但黑盒
  failure_modes: 上下文管理缺失、权限失控、追踪缺失
  related_concepts: [Agent, Tool Runtime, Context Management]
  implementation_examples: Ch19–Ch26
  evaluation: 系统评测（Ch15）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Retrieval
  chinese_name: 检索
  definition: 从外部信息源中查找与当前任务相关信息的过程。
  why_it_exists: 模型知识过时/不覆盖私有数据；上下文窗口有限
  prerequisites: [Context]
  mental_model: "Retrieval 是解决 Information Need 的确定性手段"
  alternatives: 长上下文全量注入（贵且慢）、Fine-tuning 注入知识（不当）
  tradeoffs: 相关性 vs 召回 vs 成本
  failure_modes: 召回失败、噪声注入、索引过期
  related_concepts: [RAG, Embeddings, Evaluation]
  implementation_examples: Ch28
  evaluation: Recall@K/MRR/NDCG（Ch31）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: RAG
  chinese_name: 检索增强生成
  definition: 在生成前检索外部信息并注入模型上下文的一种架构模式。RAG 是 Context Engineering 的一种实现，不是所有知识问题的默认答案。
  why_it_exists: 让生成基于可验证的外部证据
  prerequisites: [Retrieval, Context]
  mental_model: "RAG = Information Need → Retrieval → Context Construction → Generation → Evaluation"
  alternatives: Tool 直查数据库、Fine-tuning（行为而非知识）
  tradeoffs: 可溯源 vs 管道复杂度与失败模式增多
  failure_modes: 检索错、分块错、生成脱离上下文（引用不实）
  related_concepts: [Retrieval, Context Engineering]
  implementation_examples: Ch29
  evaluation: Faithfulness/Citation correctness（Ch31）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Evaluation
  chinese_name: 评测
  definition: 使用数据、指标或人工判断，对 AI 系统质量、可靠性、成本、延迟等进行测量的过程。
  why_it_exists: 概率系统没有测试就无法可靠迭代
  prerequisites: —
  mental_model: "Build → Measure → Diagnose → Change → Measure Again"
  alternatives: 人工抽查（不可扩展）、无评测（赌博）
  tradeoffs: 评测越严谨迭代越快，但建设成本越高
  failure_modes: 评测集污染、指标与业务脱节、judge 偏差
  related_concepts: [Benchmark, LLM-as-a-Judge, Observability]
  implementation_examples: Ch12–Ch17
  evaluation: —（本身即评测）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Serving
  chinese_name: 推理服务
  definition: 把模型作为稳定在线推理服务提供给上层系统的工程过程。
  why_it_exists: 模型权重和 GPU 资源需要高效共享与调度
  prerequisites: [Model, GPU/Inference 基础]
  mental_model: "Serving = 把 f(context) 变成低延迟高吞吐的在线服务"
  alternatives: API 供应商托管、本地小模型
  tradeoffs: 自部署可控/便宜 vs 托管省心/弹性
  failure_modes: OOM、长尾延迟、批处理饿死单请求
  related_concepts: [Inference, vLLM, Observability]
  implementation_examples: Ch41–Ch48
  evaluation: TTFT/TPOT/吞吐（Ch44）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

```yaml
concept:
  name: Post-training
  chinese_name: 训练后优化
  definition: 在预训练基础模型之上，通过 SFT、Preference Optimization、RL、Distillation 等手段改变模型行为和能力的过程。
  why_it_exists: 预训练模型的通用行为不总是符合业务需要
  prerequisites: [Model, Eval, 训练数据]
  mental_model: "Post-training 改变行为，不注入知识（知识用 Retrieval）"
  alternatives: Prompt、RAG、Tool（先穷尽这些再考虑训练）
  tradeoffs: 行为深度定制 vs 数据/算力成本与能力回退风险
  failure_modes: 灾难性遗忘、数据污染、过拟合评测集
  related_concepts: [SFT, LoRA, DPO, Distillation]
  implementation_examples: Ch49–Ch55
  evaluation: 训前训后同评测集（Ch55）
  source: KNOWLEDGE_CONTRACT.md
  last_verified: 2026-09-09
```

## 3. 新概念加入规则

1. 检查是否已有等价概念
2. 明确与相邻概念区别
3. 明确它解决的问题
4. 加入本表（YAML 格式）
5. 更新相关章节交叉引用

禁止无必要制造新名词。
