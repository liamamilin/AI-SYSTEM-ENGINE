# BOOK_SPEC.md

## 1. 书名

**《AI Systems Engineering：从 LLM 到 Agent、Serving 与 Post-training》**

英文副标题可使用：

**Building Reliable, Evaluated and Production-Ready AI Systems**

---

## 2. 本书定位

本书不是：

- 大语言模型数学原理教材；
- Prompt Engineering 技巧合集；
- LangChain / LangGraph / LlamaIndex 使用手册；
- RAG API 教程；
- LoRA 操作指南；
- 某一家模型厂商 SDK 文档；
- AI 新闻或工具百科。

本书是一部面向软件工程师的 **AI Systems Engineering 教材**。

核心问题是：

> 如何把一个 LLM 从“会生成文本的模型”变成一个可靠、可控、可评测、可部署、可维护、可迭代的真实 AI 系统？

---

## 3. 目标读者

默认读者具备：

- Python 基础；
- 基础数据结构和算法知识；
- 基础数据库知识；
- 基础 Web / Backend 概念；
- 基础 Linux / Docker 使用经验；
- 了解机器学习基本概念，但不要求研究级数学背景。

不默认读者已经掌握：

- Agent；
- RAG；
- LLM Serving；
- vLLM；
- Post-training；
- Eval；
- MCP；
- AI Security。

---

## 4. 能力目标

完成本书后，读者应能独立完成以下任务：

1. 分析业务问题是否需要 LLM；
2. 判断应使用普通程序、Workflow、RAG、Tool、Agent 还是 Fine-tuning；
3. 构建可靠的 LLM Interface Layer；
4. 使用 Structured Output 将 LLM 接入传统软件系统；
5. 设计 Tool Schema、Tool Runtime 和 Permission Boundary；
6. 手写并理解 Agent Loop / Agent Runtime / Harness；
7. 管理 State、Memory、Context；
8. 构建 Retrieval / RAG 系统；
9. 建立 Eval Dataset、Component Eval 和 System Eval；
10. 对 AI 系统做 Tracing、Metrics、Regression Test；
11. 设计 AI Backend、异步任务和长任务执行；
12. 处理 Retry、Timeout、Fallback、Checkpoint、Cancellation；
13. 理解 Prompt Injection、Tool Abuse、Data Exfiltration、Sandbox 等安全问题；
14. 理解并实践 MCP Client / Server；
15. 理解 LLM Inference 的 Prefill、Decode、KV Cache、Batching、Scheduling；
16. 使用 vLLM 或类似 Serving 系统部署开源模型；
17. 理解并实践 SFT、LoRA / QLoRA；
18. 理解 DPO、GRPO、RLHF、Distillation、Synthetic Data 的用途和边界；
19. 基于质量、延迟、成本、可靠性进行系统设计；
20. 完成至少一个端到端 Production AI System。

---

## 5. 技术栈层级

本书关注 L4-L6，但需要理解其上下游。

```text
L0 Hardware / Infrastructure
L1 AI Systems
L2 Model Algorithms
L3 Pre-training
L4 Post-training
L5 Model Serving / Inference
L6 AI Applications / Agents
```

重点投入：

```text
L6 > L5 > L4
```

L0-L3 只讲理解 L4-L6 所需的必要知识，不展开为研究型课程。

---

## 6. 全书核心抽象

全书优先围绕以下稳定概念组织，而不是围绕具体框架：

```text
Problem
Model
Instruction
Context
Tool
State
Memory
Runtime
Workflow
Agent
Retrieval
Data
Evaluation
Backend
Serving
Reliability
Security
Observability
Economics
Post-training
```

---

## 7. 核心系统模型

```text
AI System
=
Problem Framing
+ Model
+ Context
+ Tools
+ State
+ Runtime
+ Backend
+ Data
+ Evaluation
+ Reliability
+ Security
+ Serving
+ Economics
```

---

## 8. 三条贯穿全书的纵轴

### 8.1 Data

RAG、Eval、Memory、Post-training、Observability 都依赖数据。

### 8.2 Evaluation

任何重要修改都应经历：

```text
Build
↓
Measure
↓
Diagnose
↓
Change
↓
Measure Again
```

### 8.3 Safety / Reliability / Economics

一个系统不仅要“回答得好”，还必须：

- 不越权；
- 可恢复；
- 可观测；
- 成本可接受；
- 延迟可接受。

---

## 9. 教学哲学

### 9.1 先问题，后技术

禁止以：

> “今天我们学习 RAG。”

作为技术介绍的主要方式。

优先：

1. 现实系统遇到什么问题；
2. 普通方法为什么不够；
3. 技术因此如何产生；
4. 技术解决了什么；
5. 它引入了什么新问题。

### 9.2 从最小系统逐步演化

例如 Agent：

```text
LLM
↓
Structured Output
↓
Tool Calling
↓
Agent Loop
↓
State
↓
Error Recovery
↓
Context Management
↓
Permission
↓
Sandbox
↓
Tracing
↓
Production Agent
```

禁止一开始用大型框架掩盖底层机制。

### 9.3 先稳定抽象，后具体工具

框架只能作为实现案例。

工具可以变化，概念必须稳定。

---

## 10. 实践原则

每个重要工程主题必须至少包含：

- 一个最小实现；
- 一个可运行工程版本；
- Failure Cases；
- Trade-offs；
- Evaluation；
- Production Considerations；
- Exercises。

任何正式项目必须遵循 `CODE_STANDARD.md`。

---

## 11. 资源假设

前半本书默认：

- 普通开发电脑；
- Python；
- Git；
- Docker；
- 一个高质量 LLM API。

进入 Serving / Post-training 后：

- 可以使用租用 GPU；
- 不要求读者一开始购买 GPU；
- 本地模型作为学习对象逐步引入。

---

## 12. 成功标准

这本书成功的标准不是：

> 读者知道很多名词。

而是：

> 给读者一个真实 AI 业务问题，他能够拆解需求、做技术选择、构建系统、运行代码、建立评测、发现失败、改进系统，并解释设计权衡。

## 13. 心智模型硬性要求

本书的目标不是让读者“记住知识点”，而是让读者形成可以迁移到新问题、新框架和新模型上的稳定心智模型。

因此，每个重要主题必须帮助读者回答：

```text
这个东西是什么？
↓
为什么会出现？
↓
它解决了哪个更底层的问题？
↓
它与已有系统中的哪些部分连接？
↓
不用它会发生什么？
↓
什么时候应该使用？
↓
什么时候不应该使用？
↓
它失败时通常是哪里出了问题？
↓
我如何判断它是否有效？
```

禁止将以下内容视为充分教学：

- 罗列术语；
- 罗列 API；
- 罗列优缺点；
- 罗列框架功能；
- 罗列最佳实践；
- 给出结论但不解释因果链。

每个核心章节应至少提供一个可复用的心智模型，例如：

```text
Agent
=
Model
+ Loop
+ Tools
+ State
```

或：

```text
RAG
=
Information Need
→ Retrieval
→ Context Construction
→ Generation
→ Evaluation
```

最终要求是：

> 读者在没有记住具体 API、框架名称或代码细节时，仍然能够凭借心智模型推导出合理的系统设计。
