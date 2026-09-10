# LAST_TESTED

- status: DONE — clean install / tests pass (14) / live 冒烟通过（七环 + 引用 + 拒答）
- last verified: 2026-09-10
- environment: macOS M4 Pro 48GB, Ollama local, bge-m3 (embeddings), qwen3.5:9b-mlx (think=false), temperature=0
- deps tested: pydantic 2.13.5, httpx 0.28.1, pytest 9.1.1, uv 0.11.26, Python 3.12.14 (Homebrew)
- live smoke: 域内 query max_score=0.798 → 带 3 个引用的回答；域外 query max_score=0.150 < 0.45 → 拒答（不调 LLM）
- note: Ollama OpenAI-compat 端点忽略 think 参数（2026-09-10 实测），ollama provider 走原生 /api/chat + think=False
