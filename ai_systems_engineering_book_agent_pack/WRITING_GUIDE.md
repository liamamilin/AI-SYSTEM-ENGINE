# WRITING_GUIDE.md

## 1. 写作目标

本书必须让读者形成：

- 心智模型；
- 工程判断；
- 可运行能力；
- Debug 能力；
- Eval 能力；
- Trade-off 判断能力。

不追求：

- 名词堆积；
- 工具大全；
- API 参数大全；
- 纯理论证明；
- 伪工程案例。

---

## 2. 最核心原则：先问题，后技术

每个技术首次出现必须回答：

1. 它解决什么问题？
2. 为什么这个问题存在？
3. 如果不用它会怎样？
4. 它的替代方案是什么？
5. 它引入了哪些新问题？
6. 什么情况下不应该使用它？

禁止直接以定义开始整章。

---

## 3. 三问规则

每个核心概念至少回答：

- What is it?
- Why does it exist?
- When should I use it?

必要时增加：

- When should I NOT use it?
- What can go wrong?
- How do I know it works?

---

## 4. 从最小系统演化

优先使用：

```text
Version 0
↓
暴露问题
↓
Version 1
↓
暴露新问题
↓
Version 2
```

让读者看到“工程复杂度为什么出现”。

---

## 5. 不以框架组织知识

禁止形成：

```text
LangChain Chapter
LangGraph Chapter
LlamaIndex Chapter
```

框架只能作为案例。

稳定概念优先：

- Model
- Context
- Tool
- State
- Runtime
- Eval
- Retrieval
- Serving
- Security

---

## 6. 工程和理论比例

建议：

- 30% 原理与心智模型；
- 45% 工程实现；
- 15% Failure Cases / Trade-offs；
- 10% Eval / Exercises。

不同章节可调整。

---

## 7. 代码呈现规则

正文允许短代码用于说明概念。

但是：

**正文中的短代码不得替代正式可运行实现。**

所有正式实现必须链接/对应到 `code/` 下的完整项目。

例如：

```text
Chapter 19
正文：解释 Agent Loop

code/ch19-agent-loop/
完整可运行版本
```

详见 `CODE_STANDARD.md`。

---

## 8. 图示规则

优先使用简单 ASCII / Mermaid 风格结构表达：

```text
User
 ↓
Agent
 ↓
Tool
```

图必须服务于系统理解，不做装饰性复杂图。

---

## 9. 术语一致性

所有核心术语必须在 `GLOSSARY.md` 中登记。

首次出现：

- 中文名称；
- 英文名称；
- 定义；
- 与相邻概念区别。

后续不得任意更换定义。

---

## 10. 快速变化内容

以下信息可能快速变化：

- SDK API；
- 模型名称；
- Pricing；
- vLLM 参数；
- MCP 规范；
- 框架能力；
- 推理框架支持项。

要求：

1. 优先引用官方文档；
2. 标注验证日期；
3. 不将易变事实写成永久规律；
4. 将易变内容放入 “Current Implementation Note”。

---

## 11. 禁止事项

禁止：

- 为了增加字数重复解释；
- 用模糊类比代替正式定义；
- 给无法运行的“看起来像代码”的伪实现；
- 把 Benchmark 当作唯一判断；
- 把框架 API 当作底层原理；
- 把 Agent 神秘化；
- 把 RAG 当成所有问题答案；
- 把 Fine-tuning 当成知识库；
- 把 loss 下降等同于模型变好；
- 把一个 Demo 描述成 Production-ready。

---

## 12. 教学层次

每章至少覆盖：

```text
Understand
↓
Implement
↓
Break
↓
Measure
↓
Improve
```

读者应该亲手看到系统失败，而不是只看到“正确答案”。

## 13. Mindset-First Rule

本书禁止“知识点罗列式写作”。

技术内容必须形成：

```text
Facts
↓
Relationships
↓
Causal Model
↓
Mental Model
↓
Decision Rule
↓
Transfer
```

每章必须至少建立以下四类理解之一：

### 13.1 Structural Model

说明系统由什么组成，以及组件之间如何连接。

例如：

```text
Agent Runtime
├── Model
├── Context
├── Tools
├── State
└── Loop
```

### 13.2 Causal Model

解释为什么一个设计会导致某种结果。

例如：

```text
Context 变长
↓
Prefill 成本上升
↓
TTFT 上升
```

### 13.3 Decision Model

告诉读者遇到实际问题时如何选择。

例如：

```text
需要最新知识？
↓
优先 Retrieval / Tool

需要改变稳定行为？
↓
考虑 Post-training
```

### 13.4 Failure Model

解释系统通常如何失败，以及如何定位。

例如：

```text
回答错误
↓
是 Retrieval 错？
Context 错？
Tool 错？
Model 错？
Eval 错？
```

一个章节如果只有定义、列表、API 和代码，而没有结构、因果、决策或失败模型，不算完成。

---

## 14. Teach for Reconstruction

读者应该能够在忘记具体实现后，重新推导出方案。

因此优先教授：

```text
为什么
→ 结构
→ 约束
→ 推导
→ 实现
```

而不是：

```text
记住
→ 套模板
```

每章结束时应至少回答：

> 如果具体框架明天消失，这一章还有什么知识仍然成立？
