# KNOWLEDGE_CONTRACT.md

本文件约束全书知识体系，防止长篇 AI 写作中的 concept drift。

## 1. 核心概念记录格式

每个核心概念必须维护：

```yaml
concept:
  name:
  chinese_name:
  definition:
  why_it_exists:
  prerequisites:
  mental_model:
  alternatives:
  tradeoffs:
  failure_modes:
  related_concepts:
  implementation_examples:
  evaluation:
  source:
  last_verified:
```

---

## 2. 核心概念初始定义

### Model

执行概率生成 / 推理的模型本体。

模型不是完整 AI 系统。

---

### Instruction

告诉模型“应该如何处理当前任务”的上下文信息。

Prompt Engineering 属于 Context Engineering 的子集。

---

### Context

模型在一次推理中能够看到的信息集合。

可能包括：

- instructions；
- conversation；
- retrieved information；
- tool result；
- memory；
- environment state；
- current task state。

---

### Tool

由宿主程序提供、可由模型请求调用的确定性或外部能力。

Tool 通常包含：

```text
Name
Description
Schema
Executor
Permission
Result
```

模型提出 tool call，不等于模型自己直接执行工具。

---

### State

系统在不同执行步骤之间持久化的当前状态。

包括：

- conversation state；
- task state；
- application state；
- environment state。

---

### Memory

能够跨当前短期上下文保存、检索和重新注入信息的机制。

Memory 通常建立在 persistence + retrieval + context injection 上。

---

### Workflow

预先定义控制流的任务执行流程。

控制权主要由程序决定。

---

### Agent

能够基于模型输出动态选择下一步动作的运行系统。

简化模型：

```text
Agent
=
Model
+ Loop
+ Tools
+ State
```

Production Agent 还需要：

- context management；
- permissions；
- reliability；
- tracing；
- evaluation。

---

### Agent Runtime / Harness

负责组织模型、工具、状态、上下文和执行循环的宿主系统。

---

### Retrieval

从外部信息源中查找与当前任务相关信息的过程。

---

### RAG

在生成前检索外部信息并注入模型上下文的一种架构模式。

RAG 是 Context Engineering 的一种实现，不是所有知识问题的默认答案。

---

### Evaluation

使用数据、指标或人工判断，对 AI 系统质量、可靠性、成本、延迟等进行测量的过程。

---

### Serving

把模型作为稳定在线推理服务提供给上层系统的工程过程。

---

### Post-training

在预训练基础模型之上，通过 SFT、Preference Optimization、RL、Distillation 等手段改变模型行为和能力的过程。

---

## 3. 概念边界

必须明确区分：

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

---

## 4. 新概念加入规则

新增核心概念前：

1. 检查是否已有等价概念；
2. 明确与相邻概念区别；
3. 明确它解决的问题；
4. 加入 glossary；
5. 更新相关章节交叉引用。

禁止无必要制造新名词。
