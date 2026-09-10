# AI Systems Engineering（书稿工程仓库）

> 《AI Systems Engineering：从 LLM 到 Agent、Serving 与 Post-training》
> Building Reliable, Evaluated and Production-Ready AI Systems

面向软件工程师的 AI Systems Engineering 教材。核心问题：**如何把一个 LLM 从“会生成文本的模型”变成可靠、可控、可评测、可部署、可维护、可迭代的真实 AI 系统。**

## 目录结构

```text
ai-systems-engineering-book/
├── _quarto.yml          # Quarto 书籍配置（60 章 + 附录 A-H）
├── index.qmd            # 前言
├── content.md           # 写作蓝图（每章 goal / reader_problem / expected_output）
├── book-principles.md   # 本书特化写作原则
├── engineering-standard.md  # 统一 Python 工程规范
├── GLOSSARY.md          # 稳定术语表（防 concept drift）
├── REFERENCES.md        # 引用索引
├── STATUS.md            # 每章状态（PLANNED→…→DONE）
├── CHANGELOG.md         # 结构与定义变更记录
├── chapters/            # 章节正文（.qmd，part-00 … part-08 + appendix）
├── code/                # 章节代码项目（与章节一一对应）
├── evals/               # 共享评测设施
├── datasets/            # 样例数据
├── experiments/         # 章节计划、实验登记、结果
├── diagrams/ exercises/ solutions/ scripts/
└── references.bib
```

## 规范来源

本书全部写作规范位于 `../ai_systems_engineering_book_agent_pack/`：
BOOK_SPEC / TOC / WRITING_GUIDE / KNOWLEDGE_CONTRACT / CODE_STANDARD / CHAPTER_TEMPLATE / REVIEW_CHECKLIST / PROJECT_STRUCTURE / AGENT。

## 当前状态

- Bootstrap 完成（2026-09-09），详见 CHANGELOG.md
- 全部章节 PLANNED；章节计划已完成 Part 0（Ch1-4）+ Part 1（Ch5-11）
- 下一步：逐章写作循环（Research → Design → Code → Test → Eval → Draft → Review → DONE）

## 运行环境

- Python 3.12（uv 管理）
- 本地 LLM：Ollama（OpenAI-compatible；qwen3.5:9b-mlx / qwen3.8:27b-mlx）
- Docker 28（PostgreSQL/pgvector 等基础设施）
- Part 6/7 部分实验需租用 24GB 级 NVIDIA GPU（届时决定）
