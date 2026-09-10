# ch52-lora — Last Tested

| 项 | 值 |
|---|---|
| 日期 | 2026-09-10 |
| 机器 | Apple M4 Pro，48GB，macOS 26.6.2 |
| Python | 3.12.14（uv venv） |
| mlx-lm | 0.31.3 |
| mlx | 0.32.2 |
| transformers | 5.17.0 |
| huggingface-hub | 1.30.0 |
| pytest | 8.4.2 |

## 网络环境

- `huggingface.co` 直连超时；模型下载需 `export HF_ENDPOINT=https://hf-mirror.com`。
- 镜像的 Xet CAS 后端返回 401，须同时 `export HF_HUB_DISABLE_XET=1`（否则 snapshot_download 报 CAS Client Error 401）。
- PyPI 正常（uv 走 pypi.org）。

## 测试结果

- `PYTHONPATH=src .venv/bin/python -m pytest -q`：**58 passed**（数据 schema/配比/切分、参数映射/α=2r/dry-run、评测判分/聚合/delta、adapter 目录解析）

## 冒烟（smoke）记录——全管线真实通过

- 模型：`mlx-community/Qwen2.5-0.5B-Instruct-4bit`（~0.4GB，经 hf-mirror 下载成功）
- 数据：`examples/make_training_data.py 2 data` → 44 条（36 task + 8 general，general 占比 18.2%，配比门禁 10% 通过）→ 40 train / 4 valid（seed=42）
- 训练参数：r=8, α=16（→ MLX `lora_parameters.scale=2.0`）、lr=1e-4、num-layers=16、batch=1、iters=50、`--mask-prompt`
- 可训练参数：**0.594%**（2.933M / 494.033M）——正文的"<1%"实测
- loss 变化（每 10 iters 上报）：
  - train loss：1.096 → 0.154 → 0.075 → 0.031 → **0.024**（Iter 10→50）
  - val loss：Iter 1 = 1.159 → Iter 50 = **0.002**
  - 用时 ~5–11s；峰值显存 **0.750 GB**
- 产出：`adapters-smoke/adapters.safetensors`（+ `0000050_adapters.safetensors` 快照与 `lora_config.yaml` 留档）

### base vs LoRA 对比（ch07 30 条工单评测集，temperature=0，max_tokens=256）

| 指标 | base | LoRA | delta |
|---|---|---|---|
| schema_ok_rate | 1.000 | 1.000 | 0.000 |
| category_accuracy | 0.467 | 0.533 | **+0.067** |
| needs_human_accuracy | 0.433 | 0.567 | **+0.133** |

- 结果落盘：`results/20260910-064833/`（results.jsonl 逐条 + comparison.json 汇总）
- 结论：50 iters 冒烟量级下管线全通，目标行为两项指标真实提升（+6.7pp / +13.3pp）——schema 两模型都为 1.0（0.5B 底座本就会输出 JSON，提升空间在"选对类"与"是否需人工"，正是 LoRA 教的东西）。
- 附注：评测时 `--adapter adapters-smoke` 传**目录**（mlx-lm 0.31 语义：目录内含 adapter_config.json + adapters.safetensors）；传 `*.safetensors` 文件路径会被自动映射到其父目录。

## 9B 主线

- 命令已备好（README §4，按 mlx-lm 0.31.3 语法），未在本机执行（~6GB 下载 + 训练时长超出本次范围）。
- 显存预估（章节实测参考）：9B 4bit 底座 + LoRA ≈ 12–20GB，48GB M4 Pro 舒适运行。
