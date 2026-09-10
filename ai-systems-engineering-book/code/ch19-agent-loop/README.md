# ch19-agent-loop

> **Status: DONE**（7 mock 测试通过 + live 冒烟通过；见 LAST_TESTED.md）

## 1. 目标

不依赖任何框架，手写 Agent Loop：`Agent = Model + Loop + Tools + State`。在 Ch8 ToolLoop 之上增加：显式任务 State、真实停止条件、错误后的有界恢复。

## 2. 架构

```text
AgentLoop.run(goal, input)
  loop（有界：max_rounds / max_tool_calls / max_consecutive_errors）
    → 模型输出（协议：工具调用 JSON / finish JSON / [畸形]）
    → 解析 → registry.execute → 结果 + 状态提醒回注
    → finish → 返回（answer, stop, state, trace）
停止条件：finished | max_rounds | max_tool_calls | stall（连续失败）
```

## 3. 目录

```text
src/agent_loop.py      # AgentState（任务态）+ AgentLoop（协议/停止/恢复）
tests/test_agent_loop.py  # 7 个 mock 测试（ScriptedClient 确定性回放）
```

## 4. 运行

```bash
cd code/ch19-agent-loop
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python pytest pydantic
PYTHONPATH=src:../ch08-tool-calling/src .venv/bin/python -m pytest -q   # 7 passed
# live 冒烟：
PYTHONPATH=src:../ch08-tool-calling/src .venv/bin/python -c "
from agent_loop import AgentLoop
from tool_calling.client import make_client
from tool_calling.demo_tools import registry
out = AgentLoop(registry, max_rounds=8).run(make_client('ollama'), '计算 (37*24+115)/3 并报告', '请开始')
print(out.stop, out.answer, out.trace)"
```

## 5. 预期结果（Last verified: 2026-09-09）

- 测试：7 passed（finish/工具+状态回注/stall 连续错误/畸形输出恢复/两重上限）
- live：2 轮完成计算任务，calculator 调用 1 次，结果 334.33，stop=finished

## 6. 设计要点（正文对应）

- **State 与对话历史分离**：任务态（notes/rounds/tool_calls/errors）显式结构，每轮回注——Ch21 状态分层的雏形
- **停止条件是协议的一部分**：finish 由模型声明，上限由宿主强制
- **stall 检测**：连续 2 次同类失败 → 停止并报告部分状态，绝不假装成功
- 畸形输出：一次容忍（协议提醒重试），连续则 stall——恢复有界
