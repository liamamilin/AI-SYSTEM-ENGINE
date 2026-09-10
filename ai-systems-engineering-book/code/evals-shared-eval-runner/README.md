# evals-shared-eval-runner

> **Status: SKELETON（待实现）** — 第 13-14 章写作时完成实现并运行验证。
> 全书评测基础设施：所有章节的 eval 都通过本 runner 执行，保证格式与可复现性（Ch17）。

## 1. 目标

提供全书统一的 eval 执行器：JSONL 数据集加载、case 执行、指标计算、结果落盘（含 run 元数据：模型/prompt/dataset 版本、git commit、时间戳）。

## 2. 架构

```text
dataset.jsonl → Runner → case 执行器(各章节提供) → Metrics → results/{run_id}/
                                                                    ├── results.jsonl
                                                                    └── metadata.json  (model, prompt_ver, dataset_ver, git_commit, ts)
```

## 3. 目录

```text
src/eval_runner/
├── dataset.py      # JSONL 加载 + 版本校验
├── runner.py       # 执行循环（并发控制、失败隔离）
├── metrics.py      # 通用指标（通过率、P50/P95 延迟、成本）
tests/
└── test_runner.py  # 正常执行 / 单 case 失败隔离 / metadata 完整性
examples/
└── sample_eval.py  # 最小使用示例
```

## 4. 使用方

- ch07（解析成功率）、ch08（工具选择/参数正确率）、ch29（检索指标）、后续所有章节
