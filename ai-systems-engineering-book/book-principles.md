# Book Principles

> 本书特化写作原则。由 BOOK_SPEC.md、WRITING_GUIDE.md、AGENT.md 提炼而成。
> 与 book-writing skill 默认规则冲突时，以本文件为准；本文件修改必须记入 CHANGELOG.md。

## 1. Book Type

technical（面向软件工程师的 AI Systems Engineering 教材）。

## 2. Target Reader

具备以下基础的软件工程师：

- Python 基础、基础数据结构与算法
- 基础数据库、Web/Backend 概念
- 基础 Linux/Docker 使用经验
- 了解机器学习基本概念（不要求研究级数学）

**不默认掌握**：Agent、RAG、LLM Serving、vLLM、Post-training、Eval、MCP、AI Security。

## 3. Core Goal

> 把一个 LLM 从“会生成文本的模型”变成一个可靠、可控、可评测、可部署、可维护、可迭代的真实 AI 系统。

成功标准：给读者一个真实 AI 业务问题，他能够拆解需求、做技术选择、构建系统、运行代码、建立评测、发现失败、改进系统，并解释设计权衡。

## 4. Core Principles

1. **先问题，后技术**：每个技术首次出现必须回答——解决什么问题、为什么存在、不用会怎样、替代方案、引入什么新问题、什么时候不该用。禁止以定义开场。
2. **从最小系统演化**：Version 0 → 暴露问题 → Version 1 → 暴露新问题 → Version 2。让读者看到工程复杂度为何出现。
3. **先稳定抽象，后具体工具**：围绕 Model/Context/Tool/State/Runtime/Eval/Retrieval/Serving/Security 组织知识。框架只是实现案例。
4. **心智模型硬性要求**：每章至少建立一个可迁移心智模型（结构/因果/决策/失败模型四者至少其一，通常应覆盖多个）。读者忘记所有 API 后仍能推导出合理设计。
5. **Runnable Code**：正式实现必须可运行、实际运行过、有测试、有 eval。禁止片段拼图冒充完整项目。
6. **Eval 优先**：任何重要修改经历 Build→Measure→Diagnose→Change→Measure Again。禁止“看起来不错”作为结论。
7. **三问规则**：每个核心概念回答 What / Why / When（必要时加 When not / What can go wrong / How do I know it works）。
8. **安全必谈**：涉及工具、文件、Shell、数据库、网络的 Agent 必须显式讨论 trust boundary、permission、untrusted input、secret isolation、sandbox、approval。
9. **时效标注**：快速变化内容标注 `Last verified: YYYY-MM-DD`，放入 Current Implementation Note。

## 5. Writing Style

- 语气：直接、清楚、务实、准确、可执行
- 比例参考：30% 原理与心智模型 / 45% 工程实现 / 15% Failure Cases 与 Trade-offs / 10% Eval 与 Exercises
- 每章至少覆盖：Understand → Implement → Break → Measure → Improve（读者应亲手看到系统失败）
- 中文正文，关键术语首次出现附英文；代码/配置/API 保留英文
- 图优先用简单 ASCII/Mermaid 结构表达，服务于理解而非装饰

## 6. Required Structure

每章遵循 CHAPTER_TEMPLATE.md 的结构（问题→学习目标→前置知识→概念→心智模型→最小实现→暴露问题→工程版本→失败案例→trade-offs→生产考量→评测→实验→练习→小结→连接下一章→参考→心智模型检查）。

各章按内容性质裁剪，但以下要素**不可省略**：

- 真实工程问题开场（禁止“本章介绍……”）
- 至少一个明确心智模型
- 至少 3 个具体失败案例
- Trade-offs 与“什么时候不值得”
- Evaluation（怎么判断有效、数据集、指标、baseline）
- Exercises（Concept/Coding/Debugging/Design/Evaluation 分层）
- 与下一章的连接

## 7. Forbidden Patterns

- 知识点/API/框架功能/最佳实践的罗列式写作
- 定义开场的整章
- 用模糊类比代替正式定义
- 伪代码冒充可运行实现
- 大量“优点/缺点”列表冒充深度
- 把 Benchmark 当唯一判断
- 把框架 API 当底层原理
- 把 Agent 神秘化
- 把 RAG 当所有知识问题的答案
- 把 Fine-tuning 当知识库
- 把 loss 下降等同于模型变好
- 把 Demo 描述成 Production-ready
- 概念漂移（同一概念多名称 / 同一名称多定义）

## 8. Terminology

与 GLOSSARY.md 同步维护。核心稳定术语（首次出现写法）：

| 中文 | English | 说明 |
|---|---|---|
| 模型 | Model | 执行概率生成/推理的模型本体，不是完整 AI 系统 |
| 指令 | Instruction | 告诉模型如何处理当前任务的上下文信息 |
| 上下文 | Context | 模型一次推理中能看到的全部信息 |
| 工具 | Tool | 宿主程序提供、模型可请求调用的能力 |
| 状态 | State | 跨执行步骤持久化的当前状态 |
| 记忆 | Memory | 跨短期上下文保存、检索、重注入的机制 |
| 工作流 | Workflow | 预定义控制流的执行流程 |
| 智能体 | Agent | 基于模型输出动态选择下一步动作的运行系统 |
| 智能体运行时 | Agent Runtime / Harness | 组织模型、工具、状态、上下文与循环的宿主系统 |
| 检索 | Retrieval | 从外部信息源查找相关信息的过程 |
| 检索增强生成 | RAG | 生成前检索并注入上下文的架构模式 |
| 评测 | Evaluation | 用数据/指标/人工判断测量系统质量的过程 |
| 推理服务 | Serving | 把模型作为稳定在线推理服务的工程过程 |
| 训练后优化 | Post-training | 在预训练模型之上改变行为与能力的过程 |
