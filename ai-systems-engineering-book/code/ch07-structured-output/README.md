# ch07-structured-output

> **Status: DONE**（实现完成，已实际运行验证；见 LAST_TESTED.md 与 evals/results/）

## 1. 目标

演示如何让 LLM 输出可靠地接入传统软件：JSON Schema / Pydantic 契约、校验、失败修复（repair）与重试策略。

## 2. 架构

```text
LLM text → Extract(fence剥离/括号匹配) → Validate(Pydantic)
    → 合法 → 业务使用
    → parse/validate 失败 → Repair(error feedback 回注) → 重验（上限 max_attempts）
    → truncated(finish_reason=length) → 直接失败（不盲重试，预算是调用方决策）
```

## 3. 环境要求

- Python 3.12（uv 管理）
- 本地 Ollama（默认）或任意 OpenAI-compatible 云端点

## 4. 安装

```bash
cd code/ch07-structured-output
uv venv -p 3.12 .venv
uv pip install -p .venv/bin/python -e .
uv pip install -p .venv/bin/python pytest
cp .env.example .env   # 按需修改
```

## 5. 运行

```bash
# 最小版（单文件，走 Ollama 原生 API 关闭思考）
.venv/bin/python examples/minimal.py "耳机有杂音想退货"
# → {"category": "refund", "summary": "耳机杂音申请退货"}

# 生产版（client 抽象 + 修复循环 + 全字段 schema）
.venv/bin/python -c "
from structured_output.client import make_client
from structured_output.repair import extract_structured
v, meta = extract_structured(make_client('ollama'), '包裹丢了半个月没人管')
print(v.model_dump()); print(meta)
"
```

## 6. 测试

```bash
.venv/bin/python -m pytest -q    # 9 passed（全部 mock，不依赖 LLM）
```

## 7. Eval

```bash
.venv/bin/python evals/run_eval.py           # 30 条全量
.venv/bin/python evals/run_eval.py --limit 5 # 冒烟
```

## 8. 预期结果（Last verified: 2026-09-09, qwen3.5:9b-mlx, think off, temp 0）

```text
schema_ok_rate:        100%   （结构化提取：修复循环兜底成功）
first_pass_rate:       100%
category_accuracy:     86.7%  （30 条中 4 条分类异议）
needs_human_accuracy:  50%    （模型系统性过度保守，见正文分析）
avg_completion_tokens: ~35
```

## 9. 设计要点（正文对应）

- 截断快速失败不盲重试（预算是调用方决策）
- 错误回注精确到字段级（Pydantic errors 序列化）
- schema 是唯一事实源：校验与 prompt 格式区同源（schema_hint()）
- `needs_human` 50% 的发现是组件级评测的价值实证：**没有 eval，你不会知道模型与你的判断在哪个维度分歧**
