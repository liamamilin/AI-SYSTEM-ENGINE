# Part 0 Chapter Plans — Foundations (Ch1–4)

> 内部写作计划，正文不直接引用本文件。每章遵循 CHAPTER_TEMPLATE 流程。

---

## Ch1 — AI 技术栈与 L4-L6 定位

**Problem**：读者想“做 AI 应用”，却面对从 GPU 内核到 Prompt 技巧的无限内容；不知道哪些知识对“把模型变成系统”有用，容易被研究向内容带偏（学 Transformer 数学却不会部署服务）。

**Learning objectives**
- 给出 L0-L6 分层地图，将任意 AI 技术/工具安置到正确的层
- 区分 Research 视角与 Engineering 视角的差异
- 区分 Model 与 System：模型是系统的一个概率组件
- 理解为何本书聚焦 L4-L6（L6 > L5 > L4）

**Concepts**：L0 Hardware/Infrastructure、L1 AI Systems、L2 Model Algorithms、L3 Pre-training、L4 Post-training、L5 Serving/Inference、L6 Applications/Agents

**Mental model（结构性）**
```text
每一层回答一个问题：
L3: 能力从哪来？(预训练)
L4: 行为如何改？(Post-training)
L5: 能力如何供？(Serving)
L6: 能力如何用？(Applications/Agents)
```
决策规则：遇到任何新名词 → 先问它属于哪一层、解决该层什么问题 → 不属于 L4-L6 且非必要则跳过。

**Minimal system**：无代码章。用“给一个 API key 和一个需求，产出可用系统”的全流程走查图来展示 L4-L6 的工程环节。

**Failure cases**（≥3）
1. 团队花三个月复现论文训练，产品没有一名用户（层次错位）
2. 用“模型能力不足”解释所有问题，实际是 Context/Tool/评测缺失（把模型当系统）
3. 追新框架三个月，框架改名后知识全部失效（工具当知识）

**Eval**：章末自测——给出 10 个名词/工具，读者能正确归层并说明理由。

**Exercises**：Concept（归层练习）；Design（为自己的业务问题标注所需层）；Debugging（“上线即错”案例归因到层）。

**Connection**：Ch2 把 L6 层的“系统”拆成组件。

---

## Ch2 — AI System 的基本组成

**Problem**：工程师接上 LLM API 写了个 demo，演示成功，上线第一天崩了——因为 demo 里只有 Model，没有 State、没有 Eval、没有可靠性层。本章先给出完整地图，避免“只见模型不见系统”。

**Learning objectives**
- 说出 AI System 的 13 个组成部分及各自职责
- 对任意 AI 应用（哪怕是 demo）指出缺失了哪些组件、会以何种方式失败
- 建立“组件 ↔ 全书章节”的导航关系

**Concepts**：Model、Context、Tool、State、Runtime、Backend、Eval、Data、Infrastructure、Reliability、Security、Serving、Economics

**Mental model（结构性，全书核心）**
```text
AI System
= Problem Framing + Model + Context + Tools + State
+ Runtime + Backend + Data + Evaluation
+ Reliability + Security + Serving + Economics
```
缺组件→失败模式映射：缺 Eval→无法迭代；缺 State→任务不可恢复；缺 Security→越权/泄露；缺 Economics→成本失控；缺 Backend→长任务崩溃。

**Minimal system**：演示“只有 Model 的 demo”与“加了 State + Reliability + Eval 的 v1”在同一个失败注入（模拟 API 抖动）下的行为差异（短代码示意，正式实现属于后续章节）。

**Failure cases**
1. 无 Eval：换 prompt 全凭感觉，回归无从发现
2. 无 State：用户刷新页面，20 分钟任务消失
3. 无 Security：Agent 的 DB 工具可被注入指令窃取数据

**Eval**：给 3 个真实产品描述，读者标注已有/缺失组件并预测失败方式。

**Exercises**：Concept（组件辨析）；Design（为一个客服机器人补组件清单）；Debugging（按组件逐层排查“回答突然变差”）。

**Connection**：Ch3 解决第一个也是最容易被跳过的组件——Problem Framing。

---

## Ch3 — Problem Framing

**Problem**：“我们要用 AI 做点什么”是大多数 AI 项目失败的起点：该用规则的地方用了模型（成本高且不确定），该用模型的地方用了规则（根本做不出效果）。模型调用之前的选择决定项目生死。

**Learning objectives**
- 用确定性维度拆解业务问题
- 判断问题是否需要 LLM（概率组件）
- 用 Failure Cost 决定可接受的错误率与技术形态
- 明确 Requirements / Constraints（延迟、成本、隐私、可解释性）

**Concepts**：业务问题建模、LLM 是否必要、Deterministic vs Probabilistic、Failure Cost、Requirements/Constraints

**Mental model（决策性）**
```text
输入能否被规则/SQL 完整处理？→ 是 → 普通程序
输出错误代价高且无法容忍 1% 错误？→ 概率组件只能作辅助或必须人工兜底
任务本质是"理解/生成/转换非结构化信息"？→ 考虑 LLM
```
Failure Cost 矩阵：
```text
              错误可纠正         错误不可纠正
代价低         随便用 LLM        谨慎，加校验
代价高         必须加校验/评审    人工兜底 + 审计
```

**Minimal system**：同一“退款申请处理”需求的 3 种框架（规则 / LLM / 混合）对比，展示 Failure Cost 如何改变选型。

**Failure cases**
1. 用 LLM 判断 SQL 查询条件，错误率 2%，财务数据不可接受
2. 用硬编码规则解析用户自由文本投诉，覆盖率不足 30%
3. 未定义 Failure Cost，验收时才发现“模型不能错”，项目推翻

**Eval**：5 个业务需求 → 正确的 framing 判断 + 理由。

**Exercises**：Concept（deterministic/probabilistic 辨析）；Design（为自身业务写 Problem Framing 一页纸）；Evaluation（给三个 framing 判断错误找根因）。

**Connection**：确认需要概率组件后，下一个问题是“控制权给模型多少”——Ch4。

---

## Ch4 — Workflow vs Agent

**Problem**：团队把所有 AI 功能都写成了 Agent（成本爆炸、行为不可测），或者全部写成死板 Workflow（覆盖率低、体验差）。控制权分配是 AI 系统最重要的架构决策，却没有被当作架构决策对待。

**Learning objectives**
- 建立控制权连续谱：普通程序 → Workflow → LLM-enhanced Workflow → Agent
- 用 Autonomy Boundary 量化“给模型多少决定权”
- 列出“不应该使用 Agent”的条件

**Concepts**：普通程序、Workflow、LLM-enhanced Workflow、Agent、Autonomy Boundary

**Mental model（决策性）**
```text
任务可完全预定义？           → 普通程序/Workflow
固定流程中个别步骤需理解力？ → LLM-enhanced Workflow
任务路径不可预定义、需动态决策？ → Agent
分支：错误代价 × 可逆性 → Autonomy Boundary
```
Autonomy Boundary 三问：动作可逆吗？失败可检出吗？代价可承受吗？三否→人类审批或禁止。

**Minimal system**：同一“发票报销审核”任务的 4 种实现对比（各自代码骨架 + 行为差异表）。

**Failure cases**
1. 用 Agent 做固定三步流程：token 成本 8 倍、成功率反而下降
2. 用 Workflow 处理开放式咨询：用户换一种问法就失败
3. Agent 被赋予不可逆动作（发邮件）无审批，误发客户

**Eval**：6 个任务场景 → 正确形态选择 + Autonomy Boundary 划定。

**Exercises**：Concept（连续谱定位）；Design（为任务划定 autonomy 边界）；Debugging（“Agent 乱来”案例重新设计边界）。

**Connection**：选定形态后，需要真正理解手中的概率组件——进入 Part 1，从一次 LLM 请求的工程模型开始。
