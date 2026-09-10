# AI Systems Engineering（书稿工程仓库）

> 《AI Systems Engineering：从 LLM 到 Agent、Serving 与 Post-training》
> Building Reliable, Evaluated and Production-Ready AI Systems

面向软件工程师的 AI Systems Engineering 教材。核心问题：**如何把一个 LLM 从“会生成文本的模型”变成可靠、可控、可评测、可部署、可维护、可迭代的真实 AI 系统。**

## 目录结构

```text
ai-systems-engineering-book/
├── _quarto.yml          # Quarto 书籍配置（60 章 + 附录 A-H）
├── index.qmd            # 前言
├── engineering-standard.md  # 统一 Python 工程规范（附录 A 引用）
├── GLOSSARY.md          # 稳定术语表（防 concept drift，附录 G 以此自动生成）
├── chapters/            # 章节正文（.qmd，part-00 … part-08 + appendix）
├── code/                # 章节代码项目（与章节一一对应，tests 全部可运行）
├── evals/               # 共享评测设施
├── datasets/            # 样例数据
├── experiments/         # 实验登记表（13 条可复现记录）+ GPU 实测结果归档
├── diagrams/ exercises/ solutions/ scripts/
└── references.bib
```

## 当前状态

- 全书 60 章 + 附录 8 全部完成（Last verified: 2026-09-10）
- 9 个代码项目实测（162 测试通过）+ 13 条实验登记（vLLM 压测 / QLoRA / DPO / 蒸馏等）
- 在线书籍：https://liamamilin.github.io/AI-SYSTEM-ENGINE/（push 即自动发布）

## 运行环境

- Python 3.12（uv 管理）
- 本地 LLM：Ollama（OpenAI-compatible；qwen3.5:9b-mlx / qwen3.8:27b-mlx）
- Docker 28（PostgreSQL/pgvector 等基础设施）
- Part 6/7 部分实验需租用 24GB 级 NVIDIA GPU（届时决定）
