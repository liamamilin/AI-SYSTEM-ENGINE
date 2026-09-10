# AI Systems Engineering Book Agent Pack

本目录是一套用于驱动 AI Agent 编写《AI Systems Engineering：从 LLM 到 Agent、Serving 与 Post-training》的项目级规范。

## 使用方式

建议将本目录整体放入 Agent 可访问的项目根目录，并要求 Agent：

1. 首先阅读 `AGENT.md`；
2. 再依次阅读：
   - `BOOK_SPEC.md`
   - `TOC.md`
   - `WRITING_GUIDE.md`
   - `KNOWLEDGE_CONTRACT.md`
   - `CODE_STANDARD.md`
   - `CHAPTER_TEMPLATE.md`
   - `REVIEW_CHECKLIST.md`
   - `PROJECT_STRUCTURE.md`
3. 不得跳过规范直接批量生成整本书；
4. 以 Part 为单位规划，以 Chapter 为单位研究、实现、测试、审查和提交；
5. 每章涉及代码时，必须同时维护对应的可运行项目；
6. 每完成一个 Part，执行一次跨章节一致性审查；
7. 每完成重要代码模块，实际运行测试和示例；
8. 所有可能快速变化的技术信息应优先核对官方文档。

## 核心原则

这不是一本“AI 工具教程”，而是一本面向工程师的 AI Systems Engineering 教材。

读者完成后应能够：

- 判断一个问题是否需要 LLM；
- 在普通程序、Workflow、RAG、Tool、Agent、Fine-tuning 之间做技术选择；
- 构建 Agent Runtime / Harness；
- 建立 Eval、Tracing、Observability；
- 构建可靠的 AI Backend；
- 理解并实践模型 Serving；
- 理解并实践基础 Post-training；
- 设计、部署和评测端到端 Production AI System。

## 代码原则

**所有正式实验和项目代码必须可运行。**

禁止只给若干无法拼接的代码片段来假装完成一个工程项目。

详见 `CODE_STANDARD.md`。
