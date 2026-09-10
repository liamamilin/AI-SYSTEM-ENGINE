# ch08-tool-calling

> **Status: DONE**（实现完成，已实际运行验证；见 LAST_TESTED.md 与 evals/results/）

## 1. 目标

手写 Tool Calling 完整循环：模型提议 → 宿主校验（schema + 业务）→ 确定性执行 → 结构化结果回注 → 下一轮（有界）。建立"模型是提案人，宿主是执行人"的边界。

## 2. 架构

```text
messages → LLM → tool_call JSON?
    → ToolRegistry.lookup → 参数校验(schema 层) → Executor(业务层,确定性)
    → ToolResult(ok/value/error) → tool-role message 回注 → 下一轮
    → 非 tool_call 输出 → 最终答案
护栏: max_rounds（防失控，真停止条件见 Ch19）
```

## 3. 目录

```text
src/tool_calling/
├── registry.py     # Tool 六要素 + schema 自动生成 + 类型强制转换 + 结构化错误
├── loop.py         # 提议解析(fence/散文/裸JSON) + 回注 + max_rounds 护栏
├── demo_tools.py   # calculator(注入白名单) + get_weather(城市边界)
├── client.py       # 与 Ch7 相同的 Provider 抽象
evals/
├── tool_cases.jsonl  # 15 条：选工具/参数/幻觉工具/错误后自纠
└── run_eval.py
tests/test_loop.py  # 13 个 mock 测试
```

## 4. 安装与运行

```bash
cd code/ch08-tool-calling
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e . pytest
.venv/bin/python -m pytest -q          # 13 passed
.venv/bin/python evals/run_eval.py     # 真实模型评测
```

## 5. 预期结果（Last verified: 2026-09-09, qwen3.5:9b-mlx, think off, temp 0）

```text
tool_choice_accuracy:  93.3%   （e07: 模型心算 3/4 跳过工具——"能力捷径"倾向）
args_ok_rate:          100%
no_hallucination_rate: 100%
answered_rate:         100%
错误后自纠:             有效（结构化错误回注 → 换支持的城市重试）
```

## 6. 设计要点（正文对应）

- 错误回注格式：`{"tool":..., "error":"unsupported city: '广州' (supported: ...)"}` —— 说清哪错+怎么对，实测自纠有效
- 未知参数拒绝、类型宽容转换并全量记录
- calculator 字符集白名单，拒绝 `__import__` 注入
- 工具全只读；写工具的幂等/超时/权限是 Ch20/38 议题（本章预埋边界）
