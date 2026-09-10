# Engineering Standard

> 全书统一 Python 工程规范。所有 `code/` 项目必须遵守。
> 原则：最小但真实，不过度工程化（CODE_STANDARD §10）。

## 1. Python

- 版本：**3.12**（`requires-python = ">=3.12"`）
- 本机由 **uv** 管理版本与虚拟环境（不依赖 pyenv 全局版本）

```bash
uv python install 3.12
uv sync          # 创建 .venv 并按 lock 安装
```

## 2. 依赖与包管理

- 包管理器：**uv**（`pyproject.toml` + `uv.lock` 提交）
- 依赖声明版本范围（`>=x,<y`），禁止无版本 `pip install a b c`
- API 快速变化的库在 `LAST_TESTED.md` 记录测试版本与日期

## 3. 代码风格

- Lint + Format：**ruff**（`ruff check` / `ruff format`）
- Type checking：**mypy**（正式项目 src 目录必须通过）
- 类型注解：公共函数必须注解
- 异步：默认 async（LLM 调用章节统一 asyncio）

## 4. 测试

- 框架：**pytest**（+ pytest-asyncio）
- 分层：unit（mock/fake）→ integration（本地替代，如 Ollama）→ live（显式 `RUN_LIVE_TESTS=1`）
- 默认 CI/普通测试不依赖付费 API
- 最低覆盖：happy path / invalid input / expected failure / timeout / retry / tool error / schema validation / state transition（按项目适用）

## 5. 配置与 Secret

- 配置一律环境变量 + `.env`（被 `.gitignore` 忽略）
- 每项目提供完整 `.env.example`；禁止提交真实 key
- 命名约定：`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`（本地）；`CLOUD_*`（云供应商）；特殊用途前缀 `EVAL_*` / `RUN_*`

## 6. LLM 端点约定

- 统一 OpenAI-compatible 接口（`base_url` 抽象）
- 默认本地：`http://localhost:11434/v1`（Ollama）
  - 快速：`qwen3.5:9b-mlx`；质量：`qwen3.8:27b-mlx`
- 云端供应商只改三个环境变量，代码零改动
- live 测试默认打本地，避免费用

## 7. Docker 约定

- Production 级项目提供 `Dockerfile`（python:3.12-slim 基础）
- 多服务项目提供 `docker-compose.yml`（app / postgres / worker 模式）
- 数据库类实验统一用容器化 PostgreSQL + pgvector（Appendix C）

## 8. Eval 约定

- 数据集：JSONL（`evals/dataset.jsonl`），字段含 id / input / expected / metadata
- 执行：统一走 `evals-shared-eval-runner`
- 结果落盘：`results/{run_id}/`（results.jsonl + metadata.json，metadata 必含 model/prompt/dataset 版本、git commit、时间戳）
- 结论登记 `experiments/experiment_registry.md`

## 9. GPU 项目附加要求（Part 6/7）

- README 必须标注：最低推荐 GPU / 预计显存 / CPU 可行性 / Apple Silicon 路线（如 MLX）/ CUDA+Driver 依赖
- 云租用建议给硬件级别（如“24GB 显存级别”），不绑定具体供应商
- 无 GPU 时：提供 small-model fallback 或明确标记“此实验需 GPU”

## 10. 运行验收清单（每项目 DONE 前）

```text
[ ] clean install works (uv sync)
[ ] app starts / main entry runs
[ ] example works
[ ] tests pass
[ ] eval runs
[ ] README commands are correct
[ ] .env.example is complete
[ ] no secret committed
[ ] version info recorded (LAST_TESTED.md)
```
