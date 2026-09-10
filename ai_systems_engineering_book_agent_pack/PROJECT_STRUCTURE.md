# PROJECT_STRUCTURE.md

推荐项目目录：

```text
ai-systems-engineering-book/
│
├── README.md
├── AGENT.md
├── BOOK_SPEC.md
├── TOC.md
├── WRITING_GUIDE.md
├── KNOWLEDGE_CONTRACT.md
├── CODE_STANDARD.md
├── CHAPTER_TEMPLATE.md
├── REVIEW_CHECKLIST.md
├── PROJECT_STRUCTURE.md
│
├── GLOSSARY.md
├── REFERENCES.md
├── CHANGELOG.md
├── STATUS.md
│
├── chapters/
│   ├── part-00-foundations/
│   ├── part-01-llm-interface/
│   ├── part-02-evaluation/
│   ├── part-03-agent-systems/
│   ├── part-04-context-data/
│   ├── part-05-production/
│   ├── part-06-inference/
│   ├── part-07-post-training/
│   └── part-08-system-design/
│
├── code/
│   ├── ch07-structured-output/
│   ├── ch08-tool-calling/
│   ├── ch19-agent-loop/
│   ├── ch29-rag/
│   ├── ch33-ai-backend/
│   ├── ch47-vllm/
│   ├── ch52-lora/
│   └── capstone/
│
├── evals/
│   ├── shared/
│   └── benchmarks/
│
├── datasets/
│   ├── sample/
│   └── README.md
│
├── experiments/
│   ├── experiment_registry.md
│   └── results/
│
├── diagrams/
├── exercises/
├── solutions/
├── scripts/
└── references/
```

## 文件职责

### GLOSSARY.md
维护稳定术语。

### REFERENCES.md
全书引用索引。

### CHANGELOG.md
记录重要结构、定义和技术更新。

### STATUS.md
记录每章状态：

```text
PLANNED
RESEARCHING
DRAFT
CODE
TESTING
REVIEW
DONE
```

### experiments/
记录：

- 模型；
- prompt；
- dataset；
- config；
- code commit；
- metrics；
- conclusion。

---

## Chapter + Code 一一对应

涉及实现的章节必须能找到对应代码。

例如：

```text
chapters/part-03-agent-systems/ch19-agent-loop.md

对应

code/ch19-agent-loop/
```

不得出现正文说“完整代码见仓库”但仓库不存在的情况。
