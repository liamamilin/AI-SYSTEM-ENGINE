# CHAPTER_TEMPLATE.md

# Chapter XX — Title

## 1. 本章解决的问题

用真实工程问题开场。

回答：

- 问题是什么？
- 为什么重要？
- 现有简单方案为什么不够？

---

## 2. 学习目标

完成本章后，读者能够：

- ...
- ...
- ...

---

## 3. 前置知识

列出依赖章节。

---

## 4. 问题背景

解释现实约束。

避免先抛术语。

---

## 5. 核心概念

每个概念必须回答：

- What?
- Why?
- When?
- When not?
- Failure modes?

---

## 6. 心智模型

提供简洁模型，例如：

```text
Agent
=
Model
+ Loop
+ Tools
+ State
```

---

## 7. 系统结构

给出数据流 / 控制流。

---

## 8. Minimal Implementation

正文解释关键代码。

同时提供完整项目：

```text
code/chXX-name/minimal/
```

必须可运行。

---

## 9. 暴露问题

主动演示 minimal version 会在哪里失败。

例如：

- timeout；
- invalid schema；
- infinite loop；
- stale context。

---

## 10. Engineering Version

逐步增加：

- error handling；
- config；
- state；
- tracing；
- tests；
- eval。

完整代码：

```text
code/chXX-name/production/
```

---

## 11. Failure Cases

至少列出 3 个实际失败案例。

不是泛泛描述。

---

## 12. Trade-offs

回答：

- 得到了什么？
- 付出了什么？
- 什么场景不值得？

---

## 13. Production Considerations

考虑：

- concurrency；
- cost；
- security；
- reliability；
- monitoring；
- versioning。

---

## 14. Evaluation

明确：

- 怎么判断系统有效？
- Dataset 是什么？
- Metrics 是什么？
- Baseline 是什么？

---

## 15. Hands-on Experiment

必须给出一个可运行实验。

完整代码位于：

```text
code/...
```

---

## 16. Exercises

建议分：

### Concept
### Coding
### Debugging
### Design
### Evaluation

---

## 17. Summary

压缩为：

- Problem
- Solution
- Trade-off
- Evaluation

---

## 18. Connection to Next Chapter

解释为什么自然进入下一章。

---

## 19. References

优先：

1. 官方文档；
2. 原始论文；
3. 高质量工程博客。

快速变化资料必须标注验证日期。

## 20. Mental Model Check

每章必须显式提供至少一个“可迁移心智模型”。

应优先包含以下内容：

### Structural Model
这个系统由哪些部分组成？

### Causal Model
哪些变量变化会导致哪些结果？

### Decision Model
遇到什么条件应该选什么方案？

### Failure Model
失败时应该从哪里开始排查？

示例：

```text
LLM output 不稳定
↓
先判断：
Schema 不明确？
Context 不完整？
Model capability 不足？
Sampling 太自由？
Parser 不健壮？
```

禁止只写：

- 定义列表；
- 优点列表；
- 缺点列表；
- 工具列表。

章节完成前必须确认：

> 读者能否只凭本章的心智模型，对一个从未见过的新案例进行合理分析？
