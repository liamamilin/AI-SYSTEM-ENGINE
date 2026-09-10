# REVIEW_CHECKLIST.md

每章完成后必须执行以下审查。

# A. Technical Correctness

- [ ] 核心定义正确
- [ ] 与 KNOWLEDGE_CONTRACT 一致
- [ ] 没有混淆 Model / Agent / System
- [ ] 没有混淆 Context / State / Memory
- [ ] 没有把 RAG 当成万能方案
- [ ] 没有把 Fine-tuning 当知识库
- [ ] 技术事实有可靠来源
- [ ] 快速变化 API 已核对官方文档
- [ ] 版本和验证日期已记录

---

# B. Engineering Usefulness

- [ ] 解释了为什么需要该技术
- [ ] 解释了什么时候不需要
- [ ] 有最小实现
- [ ] 有 Failure Cases
- [ ] 有 Trade-offs
- [ ] 有 Production Considerations
- [ ] 有 Eval 方法
- [ ] 有 Debug 思路

---

# C. Code Review

- [ ] 完整项目存在
- [ ] 可以 clean install
- [ ] README 命令准确
- [ ] 主程序实际运行过
- [ ] tests 通过
- [ ] eval 可运行
- [ ] `.env.example` 完整
- [ ] 无 secret
- [ ] 依赖版本记录
- [ ] 没有用代码片段冒充完整项目

---

# D. Pedagogical Review

- [ ] 先讲问题后讲术语
- [ ] 前置知识明确
- [ ] 没有无意义术语堆积
- [ ] 有心智模型
- [ ] 从简单版本演化到工程版本
- [ ] 解释失败原因
- [ ] 章节难度合理
- [ ] 与上一章自然衔接
- [ ] 为下一章建立动机

---

# E. Concept Drift Review

- [ ] 新术语已加入 glossary
- [ ] 没有重新定义已有术语
- [ ] 交叉引用正确
- [ ] 没有出现同一概念多个名称
- [ ] 没有出现同一个名称多个定义

---

# F. AI Writing Quality

- [ ] 删除重复段落
- [ ] 删除“正确但无用”的泛话
- [ ] 删除无事实支撑的绝对判断
- [ ] 删除模板化总结
- [ ] 删除为了篇幅产生的重复案例
- [ ] 代码与正文一致

---

# G. Final Gate

只有以下全部满足才允许标记章节 DONE：

```text
Technical correctness     PASS
Runnable code             PASS
Tests                     PASS
Eval                      PASS
Pedagogical clarity       PASS
Concept consistency       PASS
References                PASS
```

# H. Mental Model Review

- [ ] 本章不是知识点罗列
- [ ] 至少有一个明确的结构模型
- [ ] 解释了关键因果关系
- [ ] 给出了实际决策规则
- [ ] 给出了失败定位模型
- [ ] 读者能解释“为什么”，而不仅是“是什么”
- [ ] 读者能将知识迁移到未见过的新场景
- [ ] 即使具体框架/API消失，本章核心知识仍然成立
- [ ] 没有用“最佳实践列表”替代理解
- [ ] 没有用类比掩盖真正机制

若本项失败，即使 Technical Correctness 和 Code 均通过，也不得标记章节 DONE。
