# BOOTSTRAP_PROMPT.md

将下面内容作为第一次交给 Agent 的任务。

---

请初始化本书项目。

首先完整阅读：

- AGENT.md
- BOOK_SPEC.md
- TOC.md
- WRITING_GUIDE.md
- KNOWLEDGE_CONTRACT.md
- CODE_STANDARD.md
- CHAPTER_TEMPLATE.md
- REVIEW_CHECKLIST.md
- PROJECT_STRUCTURE.md

然后执行以下任务，但不要开始批量写整本书：

## Task 1

按照 `PROJECT_STRUCTURE.md` 初始化目录结构。

## Task 2

创建：

- GLOSSARY.md
- REFERENCES.md
- CHANGELOG.md
- STATUS.md

根据 `KNOWLEDGE_CONTRACT.md` 填充初始 glossary。

## Task 3

审查 TOC：

检查：

- prerequisite 顺序；
- 重复章节；
- 概念遗漏；
- 章节粒度；
- 实操顺序。

只允许在有明确工程理由时修改 TOC。

所有修改写入 CHANGELOG。

## Task 4

为 Part 0 和 Part 1 创建详细 chapter plan。

暂时不要一次性生成完整正文。

## Task 5

设计第一批代码项目：

- Structured Output
- Tool Calling
- LLM Gateway
- Eval Runner

每个项目必须遵守 `CODE_STANDARD.md`。

## Task 6

创建全书统一 Python 工程规范：

- Python version
- package manager
- lint / format
- test framework
- type checking
- environment variable conventions
- Docker conventions

不要过度工程化。

## Task 7

输出项目初始化报告：

- 创建了什么；
- 修改了什么；
- 当前风险；
- 下一步建议；
- 哪些内容需要人工决策。

不要直接进入全书自动写作。
