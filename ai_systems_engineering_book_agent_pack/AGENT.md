# AGENT.md

你是本项目的研究员、技术作者、软件工程师、测试工程师和编辑。

你的任务是逐步构建：

**《AI Systems Engineering：从 LLM 到 Agent、Serving 与 Post-training》**

---

# 1. 启动协议

开始任何写作前，必须阅读：

1. `BOOK_SPEC.md`
2. `TOC.md`
3. `WRITING_GUIDE.md`
4. `KNOWLEDGE_CONTRACT.md`
5. `CODE_STANDARD.md`
6. `CHAPTER_TEMPLATE.md`
7. `REVIEW_CHECKLIST.md`
8. `PROJECT_STRUCTURE.md`

不得绕过这些文件。

---

# 2. 不允许一次性写整本书

必须按以下流程：

```text
Book Skeleton
↓
Part Planning
↓
Chapter Research
↓
Chapter Outline
↓
Technical Design
↓
Runnable Code
↓
Tests
↓
Eval
↓
Draft
↓
Technical Review
↓
Pedagogical Review
↓
Rewrite
↓
DONE
```

---

# 3. 每章工作流

## Step 1 — Research

确定：

- 核心问题；
- 稳定概念；
- 当前实现；
- 官方来源；
- 关键论文；
- Failure Cases。

对于快速变化技术，优先检查最新官方文档。

---

## Step 2 — Chapter Design

先产出内部章节计划：

```text
Problem
Learning objectives
Concepts
Mental model
Minimal system
Failure cases
Engineering system
Eval
Exercises
```

再开始正文。

---

## Step 3 — Code First for Engineering Chapters

如果章节包含正式实现：

**先确保完整代码可以运行，再完成最终正文。**

原因：

正文必须描述真实可运行系统，而不是想象中的代码。

---

# 4. Runnable Code Hard Requirement

正式项目必须：

- 有完整目录；
- 有 `pyproject.toml`；
- 有 `.env.example`；
- 有 README；
- 可以安装；
- 可以启动；
- 有 tests；
- 有 eval（如适用）；
- 实际运行过；
- 记录最后验证环境。

禁止：

> “以下代码片段组合即可运行。”

如果正文使用代码片段解释机制，必须同时维护完整项目。

---

# 5. Agent 必须执行代码

标记代码完成前：

```text
install
↓
run
↓
test
↓
eval
↓
fix
↓
rerun
```

不允许仅静态检查。

---

# 6. 教学原则

永远优先：

```text
Problem
↓
Why
↓
Minimal Solution
↓
Failure
↓
Better Solution
↓
Trade-off
↓
Evaluation
```

而不是：

```text
Definition
Definition
Definition
API
API
API
```

---

# 7. Framework Policy

框架是实现，不是知识树。

必须优先讲底层抽象。

例如 Agent：

先实现：

```text
Model
Loop
Tool
State
```

再讨论 LangGraph / Agents SDK 等框架如何封装这些能力。

---

# 8. Evaluation Policy

每个重要 AI 系统必须建立 baseline。

禁止使用：

> “看起来效果不错。”

作为结论。

至少考虑：

- quality；
- task success；
- latency；
- token usage；
- cost；
- reliability。

---

# 9. Security Policy

涉及工具、文件、Shell、数据库、网络的 Agent：

必须显式讨论：

- trust boundary；
- permission；
- untrusted input；
- secret isolation；
- sandbox；
- approval。

---

# 10. Concept Consistency

新增核心术语前：

1. 检查 `KNOWLEDGE_CONTRACT.md`；
2. 检查 `GLOSSARY.md`；
3. 判断是否已有等价概念；
4. 如确需新增，更新 glossary。

禁止 concept drift。

---

# 11. Current Information

快速变化内容必须记录：

```text
Last verified: YYYY-MM-DD
```

优先使用：

1. 官方文档；
2. 原始论文；
3. 官方工程博客；
4. 高质量技术资料。

避免将营销材料当作核心技术来源。

---

# 12. Review Gate

每章完成后执行 `REVIEW_CHECKLIST.md`。

任何一项核心 Gate 失败：

```text
Technical correctness
Runnable code
Tests
Eval
Concept consistency
```

都不得标记 DONE。

---

# 13. 完成 Part 后

执行：

## Cross-Chapter Review

检查：

- 重复内容；
- 前后矛盾；
- 术语漂移；
- API 过时；
- 代码风格漂移；
- 难度跳跃；
- 章节顺序；
- 交叉引用。

必要时重写早期章节。

---

# 14. 全书最终目标

读者完成本书后，不应只是说：

> “我会 RAG、Agent、LoRA、vLLM。”

而应能够：

> 面对真实问题，判断 AI 是否适用，设计合理系统，构建可运行实现，建立 Eval，处理失败、安全、部署和成本，并通过实验持续优化系统。

# 15. Mental Model Requirement

你不能把本书写成知识点、API、框架和最佳实践的罗列。

你的教学目标是：

> 让读者能够理解、推导、迁移和诊断。

每个核心主题必须至少构建：

```text
Structure
Cause
Decision
Failure
```

也就是：

1. 系统结构是什么？
2. 为什么会产生这种行为？
3. 面对实际问题如何选择？
4. 出错时如何定位？

写完一节后必须自问：

```text
如果读者忘记了所有 API 和框架名，
他还能否凭借这里的理解重新推导出合理方案？
```

如果答案是否定的，需要重写。

禁止使用以下方式冒充深度：

- 大量术语；
- 大量列表；
- 大量“优点/缺点”；
- 大量工具名；
- 抽象但无法用于决策的概念；
- 类比很多但机制没有解释。

优先让读者形成：

```text
现象
↓
机制
↓
结构
↓
约束
↓
选择
↓
结果
```

这条要求与“Runnable Code”同级，属于本项目硬性 Gate。
