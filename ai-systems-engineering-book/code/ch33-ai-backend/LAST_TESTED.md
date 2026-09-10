# LAST_TESTED

- status: DONE — tests pass (17) / live smoke passes (mock server 场景：同步直答 + Job 全生命周期 + 两条降级路径)
- last verified: 2026-09-10
- environment: macOS (Apple Silicon), Python 3.12.14 (uv), pytest 9.1.1, pydantic 2.x
- dependencies: 复用 ch11-model-gateway/src（PYTHONPATH 跨项目引用，未改动）
- live 冒烟：examples/mock_ollama_server.py 模拟 Ollama /api/chat，无需真实 Ollama

## 运行命令

```bash
cd code/ch33-ai-backend
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python pytest pydantic httpx
PYTHONPATH=src:../ch11-model-gateway/src .venv/bin/python -m pytest -q        # 17 passed
PYTHONPATH=src:../ch11-model-gateway/src .venv/bin/python examples/smoke_live.py  # smoke OK
```

## 冒烟摘要（2026-09-10）

1. 同步直答：route=sync status=answered degraded=False（mock 模型直答）
2. 长任务 Job：提交即断连（status=queued）→ done，progress=1.0，事件流 [accepted, queued, started, done]
3. 降级一（主模型 down）：回退层接管，degraded=True
4. 降级二（回退链耗尽）：queued_later（矩阵 queue_later）+ 后台 Job 诚实 failed
