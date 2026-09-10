# CHANGELOG.md

> 记录重要结构、定义和技术更新。格式：日期 / 变更 / 理由。

## 2026-09-10（GPU 实验日）

- **租用 GPU（RTX 4080 SUPER 32GB）三章实验全部完成**，结果归档 `experiments/gpu-2026-09-10/`：
  - **ch47-exp-001**（vLLM 0.29.0 + Qwen2.5-7B FP16/AWQ）：容量拐点 16 并发（TTFT 88→174ms 跳升，聚合吞吐 16 后趋平 556 tok/s）；prefix caching 开关实测 TTFT −50% 且高并发吞吐 +37%（556 vs 406）；AWQ L32 聚合 1349 tok/s（FP16 2.4×）；评测护航 ch07 30 条（FP16: 100/80/56.7，AWQ: 96.7/76.7/73.3）。三个真实故障入章：nvcc 过老×flashinfer、HF Xet 401、压测模型名错配
  - **ch52-exp-002**（CUDA QLoRA）：7B NF4 权重 5.45GB、峰值显存 8.56GB、可训练 0.527%（与 MLX 路线 0.594% 互相印证"<1%"）
  - **ch53-exp-001**（TRL DPO）：0.5B+30 对偏好（chosen=ch54 合成 judge≥5、rejected=自生成敷衍回复——"差距清晰"的可复现构造），margin 1.18→4.16、6.9GB、14s
- 三章各补 Current Implementation Note；实验登记表新增 3 条；ch47 实验清单 6/7 打勾（/metrics 接入留作练习）
- 本地 quarto 渲染验证通过（RStudio 内置 quarto，70/70 文件渲染成功，HTML 输出 _book/）

## 2026-09-10

- **Ch54 蒸馏实验跑通（ch54-exp-001）**：teacher 切换为 omen-alpha（Zen API，需 x-opencode-session 头；reasoning tokens 占 max_tokens）。实测漏斗 90→88(规则)→86(自审)→45(去重)：**语义去重砍掉 48%**（同工单跨温度回复高度趋同——同质化从理论项变实测结论）；teacher 自审通过率 98% 偏松，人工抽审不可省。产出 datasets/sample/ch54-{seeds,synthetic}.jsonl + experiments/ch54_distillation_report.md
- **四个代码项目落地并全部实测**：code/ch29-rag/（14 测试+live 冒烟：域内引用作答/域外拒答）；code/ch33-ai-backend/（17 测试：Job 状态机/降级矩阵/事件回放）；code/ch52-lora/（58 测试+0.5B 真训冒烟：可训练参数 0.594%、loss 1.10→0.02、评测 category +6.7pp / needs_human +13.3pp；mlx-lm 0.31 CLI 参数变更已适配）；code/capstone/（29 测试+live 冒烟：审批红线双断言/ACL fail-closed 密级零泄漏/审计回放/成本记账，32 条 5 层评测集）
- **Part 8 五章扩写**（ch56–60）：各补产物模板/Minimal Implementation（设计校验器、patch 工具链、证据链 schema、ACL 过滤+审计）、capstone 补仓库骨架与实现指引——消除收尾章节偏薄问题（4.5–6KB → 6.8–10KB）
- **ch29/ch33/ch52 章节补 Current Implementation Note**（代码已实测，接口稳定实现可换）
- 本地跑通合计：ch07/ch08/ch11/ch19/ch29/ch33/ch52/capstone 八个代码项目 118+ 新增测试全过

## 2026-09-09

### 章节进度
- **Ch56–Ch60 + 附录 A–H DONE**（全书完成）：系统设计十步法、三个 case study（coding/research/enterprise）、capstone 规格、附录速查 A–H（G 由脚本生成）。全书 audit：68 章文件齐全、frontmatter 完整、无 TODO 残留、正文总量约 31 万字
- **Ch49–Ch55 DONE**（Part 7 Post-training 完成）：训练决策树/数据工程/SFT/LoRA（Mac MLX 实测路线）/偏好优化/蒸馏/训练评测四查。全部训练实验标注双路线（Mac MLX 主线 + CUDA 租用标注）
- **Ch41–Ch48 DONE**（Part 6 Serving 完成）：推理实测（scripts/ch41_inference_experiment.py：prefill 2.8ms/token 线性、decode 恒定 36 tok/s、前缀缓存 15 倍）+ 显存账本/批处理/指标/量化/进阶优化/vLLM 实战/生产 serving。Ch47 标注 GPU 租用实验清单（本机 MLX 演练替代）
- **Ch33–Ch40 DONE**（Part 5 生产工程完成）：后端架构/长任务/系统可靠性/可观测/安全/权限/MCP/经济学。注：ch33-ai-backend 代码项目改为架构章（实现叠加于既有项目），PROJECT_STRUCTURE 相应简化
- **Ch27–Ch32 DONE**（Part 4 完成）：context 全局框架、检索机制实测（新增 nomic/bge-m3 embedding 对比：语言失配实证）、七环 RAG 管道、进阶手段账本、两级评测、数据工程。实验登记：ch28 检索三方法对比
- **Ch18–Ch26 DONE**（Part 3 Agent 系统工程完成）：ch19-agent-loop 代码项目实现（7 mock 测试 + live 冒烟：2 轮计算任务、trace/状态回注/停止条件全按协议）；Ch18 祛魅、Ch20 runtime 六层、Ch21 四层状态、Ch22 规划谱系、Ch23 记忆纪律、Ch24 上下文预算、Ch25 四级介入、Ch26 多 Agent 传递契约
- **Ch12–Ch17 DONE**（Part 2 评测工程完成）：门禁/数据集工程/组件级联/系统五维/Judge校准/可复现登记制。eval-runner 实现（4 测试通过）
- **Ch8–Ch11 DONE**（Part 1 完成）：Ch8 工具调用（13测试+15条eval：选工具93.3%/参数100%/零幻觉/错误自纠实证）；Ch9 并发（实测：本地Ollama并发收益仅25%，服务端排队所致）；Ch10 可靠性（实测：三重试策略 40%→80%→83%，放大倍数×2.4-2.5）；Ch11 网关（11测试+live冒烟：回退/degraded标记/metrics 全实证）
- **Ch5–Ch7 DONE**（Part 1 前三章）：Ch5 请求工程模型（本地实测：temperature/截断/推理token吞预算）；Ch6 指令工程（五区模板+对照实验）；Ch7 结构化输出（完整代码项目：9 测试通过、30 条 eval 实测 schema 100%/分类 86.7%/needs_human 50% 系统性分歧）。实验发现已记入工程规范：Ollama OpenAI-compat 端点忽略思考控制，本地走原生 API

- 作者定为"米霖"（_quarto.yml）
- **Ch1（AI 技术栈与 L4-L6 定位）DONE**：无代码章；REVIEW_CHECKLIST A/D/E/H PASS，代码 Gate N/A。核心产物：L0-L6 分层地图、归层决策规则（四问）、Model ≠ System 区分

### 项目初始化

- 按 PROJECT_STRUCTURE.md 建立全部目录；章节文件采用 `.qmd`（Quarto 规范）而非 `.md`，命名 `chNN-<slug>.qmd`
- 创建 `_quarto.yml`（含全部 60 章 + 附录 A-H 的章节顺序）、`index.qmd`、`references.qmd`、`references.bib`
- 创建 `content.md`（TOC.md → Quarto 写作蓝图，每章补 goal / reader_problem / expected_output）
- 创建 `book-principles.md`（BOOK_SPEC + WRITING_GUIDE + AGENT 提炼）
- 按 KNOWLEDGE_CONTRACT.md 填充 GLOSSARY.md：14 个核心概念（YAML 格式）+ 12 条概念边界
- 创建 REFERENCES.md / STATUS.md / 本文件
- 完成 TOC 审查（见下）
- 完成 Part 0（Ch1-4）+ Part 1（Ch5-11）详细 chapter plan → `experiments/chapter-plans/`
- 第一批代码项目结构落地：ch07-structured-output、ch08-tool-calling、ch11-model-gateway、evals-shared-eval-runner
- 创建 engineering-standard.md（统一 Python 工程规范）

### LLM 运行环境决策

- 默认 LLM 端点：本地 Ollama（OpenAI-compatible，`http://localhost:11434/v1`），模型 `qwen3.5:9b-mlx`（快速）/ `qwen3.8:27b-mlx`（高质量）；统一 `base_url` 抽象，换供应商零改动
- 云端模型（gpt-oss:120b-cloud / glm-5.1:cloud）保留为“teacher / 高质量模型”角色（如 Ch54 蒸馏）
- Serving（Part 6）实战需租用 24GB 级 NVIDIA GPU；Post-training（Part 7）提供 MLX 本地路线（M4 Pro 48GB 可跑 9B LoRA）与 CUDA 云端路线双轨

### TOC 审查记录

经审查，**保持 TOC 原有章节顺序不变**（保守原则），仅在 content.md 中补充以下标注：

1. **Ch31（Retrieval Evaluation）前置依赖标注**：它位于 Ch30 之后，但内容依赖 Ch28-29。写作时明确标注前置，Ch30 与 Ch31 可独立阅读。理由：Ch30（Advanced Retrieval）的每种优化都必须用 Ch31 的指标验证，故顺序应为 30→31 而非 31→30；无需调序，但需在两章开头互相交叉引用。
2. **Ch10 与 Ch35 层次切分**：两者主题重叠（Retry/Fallback/Timeout）。已明确：Ch10 = 单次模型调用层的可靠性；Ch35 = 系统层可靠性（熔断/幂等/降级）。写作 Ch35 时必须回引 Ch10 并只讲系统层增量。
3. **Ch24 与 Ch27 分工**：Ch24 = Agent 运行时内的上下文管理（机制）；Ch27 = 全局 Context Engineering（决策）。两章开头互设交叉引用，避免重复。
4. **Appendix A（Python/Async）与 Ch9 的关系**：Appendix A 只做速查，async 的教学责任在 Ch9；Appendix A 标注“先读 Ch9 需要的最低限度即可”。
5. **Ch3 位置确认**：Problem Framing（Ch3）在 Ch4（Workflow vs Agent）之前是正确的依赖顺序（先判断是否需要 LLM，再选形态），不调整。
6. **粒度检查**：60 章粒度均匀，无内容重复的章节；无遗漏关键主题（MCP、Security、Economics 均有归属）。不改。

### 已知风险（初始化时点）

- 本机 Python 为 3.10（pyenv），工程规范要求 3.12 → 由 `uv` 管理 Python 版本解决
- `qwen3.8:27b-mlx` 需 18GB 内存，与其他应用并存时需注意内存压力
- Ch47/Ch52(CUDA 路线)/Ch53 实验依赖租用 GPU，预算与时机需在 Part 6 前确认
- Ollama 云端模型计费额度未知，Ch54 蒸馏实验前需确认
