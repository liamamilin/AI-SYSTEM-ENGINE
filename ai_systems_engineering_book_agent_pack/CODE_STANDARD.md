# CODE_STANDARD.md

# 0. 最高规则

**所有正式实验、项目、章节实现必须提供可运行版本。**

正文可以存在教学性代码片段，但代码片段不能替代完整项目。

“可运行”意味着读者能够按照文档，在干净环境中复现运行结果。

---

# 1. 每个正式代码项目必须包含

最低结构：

```text
code/chXX-project-name/
├── README.md
├── pyproject.toml
├── .env.example
├── src/
├── tests/
└── scripts/          # 如有需要
```

也可根据项目需要增加：

```text
docker/
Dockerfile
docker-compose.yml
configs/
data/
evals/
migrations/
```

---

# 2. README 必须包含

每个项目的 `README.md` 必须明确：

## 2.1 目标

这个项目演示什么？

## 2.2 架构

系统组成和数据流。

## 2.3 环境要求

例如：

```text
Python 3.12
Docker 27+
PostgreSQL 17
```

不要使用“最新版”作为唯一说明。

## 2.4 安装

必须给完整命令。

例如：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2.5 配置

必须提供 `.env.example`。

不得提交真实 API Key。

## 2.6 运行

例如：

```bash
python -m app.main
```

或：

```bash
uvicorn app.main:app --reload
```

## 2.7 测试

例如：

```bash
pytest -q
```

## 2.8 Eval

如属于 AI 模块，必须说明如何执行 eval。

## 2.9 预期结果

读者应该看到什么？

---

# 3. 依赖必须可复现

推荐使用：

```text
pyproject.toml
```

明确依赖版本范围。

禁止：

```text
pip install openai langchain ...
```

然后不记录版本。

当 API 快速变化时：

- 记录测试版本；
- 写入 `LAST_TESTED.md` 或 README；
- 标明验证日期。

---

# 4. 所有重要项目必须实际运行

Agent 在标记项目为完成前必须：

1. 安装依赖；
2. 执行主要程序；
3. 执行测试；
4. 执行关键 Eval；
5. 修复失败；
6. 记录最后测试环境。

禁止：

> “代码理论上可以运行。”

必须真的运行。

---

# 5. 测试要求

最低测试：

- happy path；
- invalid input；
- expected failure；
- timeout / retry（如适用）；
- tool error（Agent 项目）；
- schema validation（Structured Output）；
- state transition（Agent Runtime）。

Production 章节还应覆盖：

- idempotency；
- cancellation；
- fallback；
- permissions；
- concurrency。

---

# 6. API Key 和 Secret

禁止：

- 硬编码 API Key；
- 把真实 secret 写进仓库；
- 在测试输出中泄漏密钥。

统一：

```text
.env
.env.example
```

`.env` 必须被 `.gitignore` 忽略。

---

# 7. 外部 API 测试

测试分为：

```text
unit tests
integration tests
live tests
```

默认 CI / 普通测试不应强依赖付费 API。

推荐：

- unit test 使用 mock / fake；
- integration test 可使用本地替代；
- live test 显式开启。

例如：

```bash
RUN_LIVE_TESTS=1 pytest tests/live
```

---

# 8. 不允许“片段拼图式工程”

禁止一个章节提供：

```python
# snippet A
...

# snippet B
...

# snippet C
...
```

然后声称：

> 组合起来就是完整 Agent。

必须同时提供：

```text
code/ch19-agent-loop/
```

完整版本。

---

# 9. 教学代码与 Production 代码区分

允许存在：

```text
minimal/
production/
```

例如：

```text
code/ch19-agent-loop/
├── minimal/
└── production/
```

Minimal：

- 追求可理解；
- 尽量少依赖；
- 暴露核心机制。

Production：

- error handling；
- configuration；
- tests；
- logging；
- type hints；
- observability。

---

# 10. 禁止过度抽象

代码必须服务于当前章节学习目标。

禁止为了“架构漂亮”提前引入：

- 多层 factory；
- 无意义 repository pattern；
- 复杂 DI container；
- 不必要 microservices；
- 多 Agent；
- 大型 framework。

优先：

> 最小但真实。

---

# 11. Framework Policy

前期核心机制优先手写。

例如：

Agent Loop 必须至少有一个不依赖大型 Agent Framework 的实现。

随后可以增加：

```text
framework-version/
```

用于展示生产框架如何映射到底层抽象。

---

# 12. 数据要求

任何 Eval / RAG / Training 项目：

- 提供最小可运行样例数据；
- 说明数据来源；
- 禁止假设用户拥有未提供的数据；
- 大数据集可提供下载脚本；
- 下载脚本必须有错误提示和校验。

---

# 13. Docker

Production 级项目尽可能提供：

```text
Dockerfile
```

涉及多个服务时提供：

```text
docker-compose.yml
```

例如：

```text
app
postgres
worker
```

---

# 14. GPU 项目

Serving / Post-training 代码必须明确：

- 最低推荐 GPU；
- 预计显存；
- CPU 是否可运行；
- Apple Silicon 是否支持；
- CUDA / Driver 依赖；
- 推荐云 GPU 方案的硬件级别，而不是绑定具体供应商。

如果没有 GPU：

- 提供 CPU / small model fallback（如果合理）；
- 或明确标记此实验需要 GPU。

---

# 15. Eval 是代码的一部分

AI 项目不能只有：

```text
src/
```

还应该尽可能包含：

```text
evals/
```

例如：

```text
evals/
├── dataset.jsonl
├── run_eval.py
├── metrics.py
└── baseline.json
```

---

# 16. 运行验收

每个项目完成前执行：

```text
[ ] clean install works
[ ] app starts
[ ] example works
[ ] tests pass
[ ] eval runs
[ ] README commands are correct
[ ] .env.example is complete
[ ] no secret committed
[ ] version info recorded
```

只有全部满足，项目才可标记为 DONE。
