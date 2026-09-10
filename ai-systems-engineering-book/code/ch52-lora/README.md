# ch52-lora

> **Status: DONE**（mock 测试全过 + 小模型冒烟全管线通过；见 LAST_TESTED.md）

Ch52《LoRA and QLoRA》配套实现：**MLX 本地 LoRA 微调路线**——数据准备（chat JSONL 校验/配比/切分）、`mlx_lm lora` 训练封装（参数映射 + dry-run）、基础 vs LoRA 同评测集对比（复用 ch07 的 30 条工单评测集）。

## 1. 目标

- Ch51 数据格式（`{"messages": [...]}` JSONL）的产线化准备：schema 校验、Ch50 配比门禁（general 占比）、确定性 train/val 切分；
- 章节主线命令的参数映射（r/α/targets/lr/底座）显式可测，**α=2r 惯例内置**（α<r 的"有效缩放过弱"静默失败在构命令前拦截——章节案例二）；
- 训前基线 → 训练 → 训后同集对比的强制流程（Ch51 三段评测纪律）。

## 2. 目录

```text
src/lora_lab/
  data_prep.py     # chat JSONL 校验 + 配比门禁 + 确定性切分
  train.py         # TrainConfig -> mlx_lm CLI argv 映射 + dry-run + loss 解析
  eval_compare.py  # base vs LoRA 同评测集对比（ch07 dataset.jsonl，简化 runner）
tests/             # mock 测试（不依赖真实训练）
examples/
  make_training_data.py  # 生成冒烟训练数据（工单分类任务 + general 混入）
  run_smoke.sh           # 小模型全管线冒烟
results/           # 评测落盘 results/{ts}/（results.jsonl + comparison.json）
```

## 3. 运行

```bash
cd code/ch52-lora
uv venv -p 3.12 .venv
uv pip install -p .venv/bin/python "mlx-lm>=0.31,<1" "pytest>=8,<9"
PYTHONPATH=src .venv/bin/python -m pytest -q   # 58 passed（Last verified: 2026-09-10）
```

冒烟（小模型，≤1GB，全管线）：

```bash
zsh examples/run_smoke.sh
# 默认模型：mlx-community/Qwen2.5-0.5B-Instruct-4bit（~0.4GB）
# 步骤：磁盘检查 -> 数据准备 -> dry-run -> 50 iters LoRA 训练 -> base vs LoRA 评测对比
# 结果实测见 LAST_TESTED.md（含 loss 曲线与对比数字）
```

## 4. 9B 主线命令（M4 Pro 48GB 本机可跑，章节实测）

**注意：以下按 mlx-lm 0.31.3 语法书写**（章节正文里的命令是旧版 CLI：`--data train.jsonl` 单文件、`--rank/--alpha` 开关在新版已移入 `-c` 配置）。r/α 经 YAML 的 `lora_parameters` 传入——MLX 的 `scale` 是低秩更新直接乘子（`h = Wx + scale·B(Ax)`），与章节公式 `h = Wx + (α/r)·B(Ax)` 对照即 **scale = α/r**（α=2r → scale=2.0）；本项目的 `TrainConfig` 已封装该映射（`train.py:write_lora_config`）。

```bash
# 底座：MLX 4bit 量化 repo（QLoRA 思想：冻结权重本身 4bit，~6GB 下载）
# 以实际 mlx-community repo id 为准（按 mlx-community/<qwen3.5-9b-4bit> 检索，示例名如下）
# 直接复用本封装（推荐——命令映射、YAML 留档、loss 解析都是测过的代码）：
PYTHONPATH=src .venv/bin/python -c "
from lora_lab.train import dry_run, run_training, TrainConfig
cfg = TrainConfig(model='mlx-community/Qwen3.5-9B-4bit', data='data',
                  rank=32, iters=3000, batch_size=1, learning_rate=1e-4,
                  num_layers=16, adapter_path='adapters-9b', save_every=200)
dry_run(cfg)        # 先肉眼审命令（r=32/α=64→scale=2.0, lr=1e-4, 后 16 层, mask-prompt）
run_training(cfg)   # 确认无误再真跑
"
# 等价的裸 mlx_lm 命令（dry-run 打印的内容，含自动生成的 -c adapters-9b/lora_config.yaml）：
#   python -m mlx_lm lora --train --model mlx-community/Qwen3.5-9B-4bit \
#     --data data --fine-tune-type lora --num-layers 16 --batch-size 1 \
#     --iters 3000 --learning-rate 0.0001 --mask-prompt --seed 42 \
#     --adapter-path adapters-9b --save-every 200 \
#     -c adapters-9b/lora_config.yaml   # lora_parameters: {rank: 32, scale: 2.0}

# 训后：同评测集对比（第 51/55 流程；--adapter 传目录，mlx-lm 0.31 语义）
PYTHONPATH=src .venv/bin/python -m lora_lab.eval_compare \
  --base-model mlx-community/Qwen3.5-9B-4bit \
  --adapter adapters-9b
```

显存量级（章节实测参考）：9B + 4bit 底座 + LoRA ≈ 12–20GB，48GB M4 Pro 舒适运行。

### 9B 主线 vs 小模型冒烟的区别

| | 小模型冒烟（2026-09-10 实测通过） | 9B 主线 |
|---|---|---|
| 底座 | Qwen2.5-0.5B-Instruct-4bit（~0.4GB） | 9B 4bit（~6GB 下载） |
| iters | 50（管线验证，~10s） | 数千（epochs=3 换算 iters，按数据量） |
| r/α | 8/16（scale=2.0，格式类任务起点） | 32/64（复杂行为；正文 Coding 实验 r=8 vs r=32 各一） |
| 目的 | 验证管线端到端 | 真实行为微调 + rank 容量对比 |
| 显存 | 0.750 GB（实测峰值） | 12–20GB |

冒烟实测（详见 LAST_TESTED.md）：train loss 1.096→0.024（50 iters），val loss 1.159→0.002；评测集对比 category_accuracy +6.7pp、needs_human_accuracy +13.3pp。

**冒烟的意义**：9B 下载与训练重（小时级），先用 0.5B 把"数据→训练→评测对比"管线全部跑通、验证命令与判分逻辑，再换底座上主线——换底座只改 `--model` 与 iters，管线代码零改动。

## 5. 预期结果（Last verified: 2026-09-10）

见 LAST_TESTED.md（测试数、冒烟 loss 变化、base vs LoRA 对比数字）。

## 6. 设计要点（正文对应）

- **数据门禁前置**：schema 校验 + general 配比门禁（Ch50）+ 确定性切分（Ch17）在训练之前，不过门禁不训练；
- **dry-run 是纪律**：训练命令先打印后执行——参数因果（r/α/lr/num-layers）肉眼可审；
- **α=2r 惯例内置**：`alpha=None -> 2*rank`；α/r<1 直接报错（章节案例二：α=8, r=32 的静默失败）；
- **loss 只是仪表**：训练封装解析 loss 流水仅供监控，成败判定只在 eval_compare（Ch51 三信号诊断）；
- **评测集复用**：`find_default_dataset()` 定位 `code/ch07-structured-output/evals/dataset.jsonl`（30 条工单），base 与 LoRA 用同一集、同一判分；
- **底座×适配器组合资产**（章节案例三）：eval_compare 必须给 `--base-model`，`--adapter` 可选（不给则仅跑 base 基线——Ch51"训前基线"纪律）；结果 metadata 记录两者——版本绑定纪律。

## 7. 网络注意

若 `huggingface.co` 直连超时，设 `export HF_ENDPOINT=https://hf-mirror.com` 后再下载模型（huggingface_hub 遵循此变量）；**镜像的 Xet CAS 后端会 401，需同时 `export HF_HUB_DISABLE_XET=1`**（2026-09-10 实测，run_smoke.sh 已内置）。
