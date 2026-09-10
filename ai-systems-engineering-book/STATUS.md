# STATUS.md

> 每章状态记录。状态机：PLANNED → RESEARCHING → DRAFT → CODE → TESTING → REVIEW → DONE
> 章节级 DONE 的硬性 Gate：Technical correctness / Runnable code / Tests / Eval / Pedagogical clarity / Concept consistency / References 全部 PASS（REVIEW_CHECKLIST.md）。

## Part 0 — Foundations

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 01 | AI 技术栈与 L4-L6 定位 | ch01-ai-stack.qmd | DONE | 无代码章（概念/地图章），代码 Gate N/A；初稿+自检通过 2026-09-09 |
| 02 | AI System 的基本组成 | ch02-system-components.qmd | DONE | 无代码章；13 组件地图+缺组件失败映射；2026-09-09 |
| 03 | Problem Framing | ch03-problem-framing.qmd | DONE | 无代码章；Framing 一页纸模板；2026-09-09 |
| 04 | Workflow vs Agent | ch04-workflow-vs-agent.qmd | DONE | 无代码章；连续谱+Autonomy Boundary 三问；2026-09-09 |

## Part 1 — LLM Interface Engineering

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 05 | LLM 请求的工程模型 | ch05-llm-request-model.qmd | DONE | 本地实测验证（scripts/ch05_experiments.py + ch05_native_check.py）；发现推理token吞预算实证；2026-09-09 |
| 06 | Instruction & Prompt Engineering | ch06-instruction-prompt.qmd | DONE | 五区模板+20条对照实验数据；2026-09-09 |
| 07 | Structured Output | ch07-structured-output.qmd | DONE | 代码项目实现+9测试通过+30条eval实测（schema 100%/分类86.7%/needs_human 50%）；2026-09-09 |
| 08 | Tool Calling | ch08-tool-calling.qmd | DONE | 代码项目实现+13测试+15条eval实测（选工具93.3%/参数100%/零幻觉）；2026-09-09 |
| 09 | Streaming, Async and Concurrency | ch09-streaming-async.qmd | DONE | 实测：并发/限流/TTFT（scripts/ch09_concurrency_experiment.py）；2026-09-09 |
| 10 | Reliability of Model Calls | ch10-reliability.qmd | DONE | 实测三策略对比（scripts/ch10_retry_experiment.py：40%/80%/83%，放大×2.4-2.5）；2026-09-09 |
| 11 | Model Gateway and Routing | ch11-model-gateway.qmd | DONE | 代码项目实现+11测试+live冒烟（回退/degraded/metrics实证）；2026-09-09 |

## Part 2 — Evaluation & Experiment Engineering

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 12 | Why Eval Is Core Engineering | ch12-why-eval.qmd | DONE | 门禁脚本设计+三层失败案例；2026-09-09 | |
| 13 | Eval Dataset Engineering | ch13-eval-dataset.qmd | DONE | 噪声数学+难度三层+指纹；2026-09-09 | |
| 14 | Component Evaluation | ch14-component-eval.qmd | DONE | 级联定位表+复用ch07/08实测；2026-09-09 | 投入使用 eval-runner |
| 15 | System Evaluation | ch15-system-eval.qmd | DONE | 五维+乘性衰减实证43%；2026-09-09 | |
| 16 | LLM-as-a-Judge | ch16-llm-as-judge.qmd | DONE | 三范式+偏差缓解+校准实验；2026-09-09 | |
| 17 | Experiment Reproducibility | ch17-reproducibility.qmd | DONE | 五要素+登记制+复现演习；2026-09-09 | |

## Part 3 — Agent Systems Engineering

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 18 | What Is an Agent? | ch18-what-is-agent.qmd | DONE | 祛魅+四要素+自主三刻度；2026-09-09 | |
| 19 | Build an Agent Loop From Scratch | ch19-agent-loop.qmd | DONE | 代码项目：7测试+live冒烟（2轮计算任务）；2026-09-09 | 手写循环，不依赖框架（硬性要求） |
| 20 | Tool Runtime | ch20-tool-runtime.qmd | DONE | 六层runtime管线+写读分流；2026-09-09 | |
| 21 | State | ch21-state.qmd | DONE | 四层状态+checkpoint/resume；2026-09-09 | |
| 22 | Planning | ch22-planning.qmd | DONE | 规划谱系+重规划触发；2026-09-09 | |
| 23 | Memory | ch23-memory.qmd | DONE | 记忆分类+注入三纪律；2026-09-09 | |
| 24 | Context Management | ch24-context-management.qmd | DONE | 预算学+四手段；2026-09-09 | 与 Ch27 分工见 CHANGELOG |
| 25 | Human-in-the-loop | ch25-human-in-the-loop.qmd | DONE | L0-L3介入+审批流；2026-09-09 | |
| 26 | Multi-Agent and Sub-Agent | ch26-multi-agent.qmd | DONE | 三模式+传递契约+Agent即工具；2026-09-09 | |

## Part 4 — Context, Retrieval, Knowledge and Data

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 27 | Context Engineering | ch27-context-engineering.qmd | DONE | 六来源+四问+三通道；2026-09-09 | |
| 28 | Retrieval Fundamentals | ch28-retrieval-fundamentals.qmd | DONE | BM25手写+三方法实测（语言失配实证）；2026-09-09 | |
| 29 | RAG Pipeline | ch29-rag-pipeline.qmd | DONE | 七环管道+分层归因；2026-09-09 | 代码项目：code/ch29-rag/（14 测试+live 冒烟，2026-09-10） |
| 30 | Advanced Retrieval | ch30-advanced-retrieval.qmd | DONE | 失败模式×手段账本；2026-09-09 | |
| 31 | Retrieval Evaluation | ch31-retrieval-eval.qmd | DONE | 两级指标+联动诊断；2026-09-09 | 依赖 Ch28-29，见 CHANGELOG |
| 32 | Data Engineering for AI Systems | ch32-data-engineering.qmd | DONE | 血缘+版本+契约；2026-09-09 | |

## Part 5 — Production AI Engineering

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 33 | AI Backend Architecture | ch33-ai-backend.qmd | DONE | 七组件架构+Job分流；2026-09-09 | 代码项目：code/ch33-ai-backend/（17 测试+mock 冒烟，2026-09-10） |
| 34 | Long-running Tasks | ch34-long-running-tasks.qmd | DONE | 队列语义+checkpoint生产化；2026-09-09 | |
| 35 | Reliability Engineering | ch35-reliability-engineering.qmd | DONE | 熔断/舱壁/降级/预算；2026-09-09 | 与 Ch10 层次切分见 CHANGELOG |
| 36 | Observability | ch36-observability.qmd | DONE | trace+质量信号+成本聚合；2026-09-09 | |
| 37 | AI Security | ch37-ai-security.qmd | DONE | 七威胁+三层防御；2026-09-09 | |
| 38 | Sandbox and Permission Systems | ch38-sandbox-permission.qmd | DONE | 能力模型+沙箱分级；2026-09-09 | |
| 39 | MCP and Tool Protocols | ch39-mcp.qmd | DONE | 三原语+双端安全；2026-09-09 | 标注 MCP 规范版本 |
| 40 | AI Economics | ch40-ai-economics.qmd | DONE | 两级账+手段账+价值框架；2026-09-09 | |

## Part 6 — Model Serving & Inference Engineering

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 41 | LLM Inference Fundamentals | ch41-inference-fundamentals.qmd | DONE | 两阶段+KV+前缀缓存（本地实测2.8ms/token、缓存15倍）；2026-09-09 | Mac MLX 先行 |
| 42 | GPU Memory | ch42-gpu-memory.qmd | DONE | 三笔账+速算工作流；2026-09-09 | 公式+租用 GPU 验证 |
| 43 | Batching and Scheduling | ch43-batching-scheduling.qmd | DONE | 三级批处理范式；2026-09-09 | GPU 实验需租用 |
| 44 | Inference Metrics | ch44-inference-metrics.qmd | DONE | 三指标+分位纪律；2026-09-09 | |
| 45 | Quantization | ch45-quantization.qmd | DONE | 量化谱系+评测护航；2026-09-09 | |
| 46 | Advanced Inference | ch46-advanced-inference.qmd | DONE | 瓶颈×七技术对照表；2026-09-09 | |
| 47 | vLLM as a Serving Case Study | ch47-vllm-case-study.qmd | DONE | vLLM实战；2026-09-10 | ch47-exp-001 已实测（RTX 4080 SUPER 32GB：拐点 16 并发、prefix cache TTFT-50%/吞吐+37%、AWQ 2.4×，租卡清单中的实验完成） |
| 48 | Production Serving | ch48-production-serving.qmd | DONE | 生产serving五件套；2026-09-09 | |

## Part 7 — Post-training Engineering

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 49 | When Should You Train? | ch49-when-to-train.qmd | DONE | 五枝决策树+立项五门禁；2026-09-09 | |
| 50 | Dataset Engineering for Post-training | ch50-dataset-for-post-training.qmd | DONE | 六步门禁+污染隔离；2026-09-09 | |
| 51 | Supervised Fine-Tuning | ch51-sft.qmd | DONE | SFT机制+MLX实测路线；2026-09-09 | MLX 或租 GPU |
| 52 | LoRA and QLoRA | ch52-lora-qlora.qmd | DONE | LoRA机制+Mac实测路线；2026-09-10 | 双路线：MLX 本地 / CUDA 云端；code/ch52-lora/（58 测试+0.5B 真训冒烟：可训练参数 0.594%、category +6.7pp） |
| 53 | Preference Optimization | ch53-preference-optimization.qmd | DONE | 三方法谱系+黑客防御；2026-09-10 | ch53-exp-001 已实测（TRL DPO 0.5B：30 对、margin 1.18→4.16、6.9GB） |
| 54 | Synthetic Data and Distillation | ch54-synthetic-data-distillation.qmd | DONE | 蒸馏流水线+四风险；2026-09-10 | teacher=omen-alpha（Zen API）；ch54-exp-001 已跑通（90→45 条合成集） |
| 55 | Post-training Evaluation | ch55-post-training-eval.qmd | DONE | 四查流程+金标准；2026-09-09 | |

## Part 8 — End-to-End AI System Design

| NN | Chapter | File | Status | Notes |
|---|---|---|---|---|
| 56 | AI System Design Method | ch56-system-design-method.qmd | DONE | 设计方法总纲+产物模板+设计校验器；2026-09-10 | |
| 57 | Coding Agent Case Study | ch57-coding-agent-case.qmd | DONE | 编码 Agent 案例+patch 工具链；2026-09-10 | |
| 58 | Research Agent Case Study | ch58-research-agent-case.qmd | DONE | 研究 Agent 案例+证据链 schema；2026-09-10 | |
| 59 | Enterprise Knowledge Agent | ch59-enterprise-knowledge-agent.qmd | DONE | 企业知识 Agent 案例+ACL 过滤实现；2026-09-10 | |
| 60 | Capstone: Production AI Agent Platform | ch60-capstone.qmd | DONE | 毕业项目；code/capstone/（29 测试+live 冒烟+32 条评测集，2026-09-10） |

## Appendix

| ID | Title | File | Status | Notes |
|---|---|---|---|---|
| A | Python / Async refresher | appendix-a-python-async.qmd | DONE | Python/Async 速查；2026-09-09 | |
| B | Docker / Linux refresher | appendix-b-docker-linux.qmd | DONE | Docker/Linux 速查；2026-09-09 | |
| C | PostgreSQL / pgvector | appendix-c-postgres-pgvector.qmd | DONE | Postgres/pgvector 速查；2026-09-09 | |
| D | GPU basics | appendix-d-gpu-basics.qmd | DONE | GPU 基础与租用指南；2026-09-09 | 含租用 GPU 指南 |
| E | Multimodal AI | appendix-e-multimodal.qmd | DONE | 多模态坐标系；2026-09-09 | 选读 |
| F | Framework comparison | appendix-f-framework-comparison.qmd | DONE | 框架映射表；2026-09-09 | |
| G | Glossary | appendix-g-glossary.qmd | DONE | 由 GLOSSARY 自动生成；2026-09-09 | 由 GLOSSARY.md 同步生成 |
| H | Current ecosystem notes | appendix-h-ecosystem.qmd | DONE | 生态追踪方法；2026-09-09 | |

## 汇总

- 总章节：60 + 附录 8
- DONE：68（全书 60 章 + 附录 8 全部完成）
- 进行中：0
- PLANNED：0
