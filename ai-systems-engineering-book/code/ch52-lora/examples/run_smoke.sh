#!/bin/zsh
# ch52 冒烟：小模型（≤1GB）全管线——数据准备 -> dry-run -> LoRA 训练（少量 iters）-> 基础 vs LoRA 评测对比
# 用法：zsh examples/run_smoke.sh [SMOKE_MODEL]
set -euo pipefail
cd "$(dirname "$0")/.."

SMOKE_MODEL="${1:-mlx-community/Qwen2.5-0.5B-Instruct-4bit}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"   # huggingface.co 直连失败时的镜像
export HF_HUB_DISABLE_XET=1   # 镜像的 Xet CAS 后端 401，禁用走普通 HTTP（实测必要，见 LAST_TESTED.md）
PY=.venv/bin/python

echo "== 1. 磁盘检查（需 >=20GB 可用）=="
df -h / | tail -1

echo "== 2. 训练数据准备（schema 校验 + 配比门禁 + train/valid 切分）=="
$PY examples/make_training_data.py 2 data

echo "== 3. dry-run：先看命令（r/alpha 经 -c config.yaml 传入），不执行 =="
PYTHONPATH=src $PY -c "
from lora_lab.train import dry_run, TrainConfig
cfg = TrainConfig(model='$SMOKE_MODEL', data='data',
                  rank=8, iters=50, batch_size=1, learning_rate=1e-4,
                  num_layers=16, adapter_path='adapters-smoke', save_every=50)
dry_run(cfg)
"

echo "== 4. 真实 LoRA 训练（50 iters, r=8, α=16→scale=2.0, lr=1e-4, 后 16 层, mask-prompt）=="
PYTHONPATH=src $PY -c "
from lora_lab.train import run_training, TrainConfig
cfg = TrainConfig(model='$SMOKE_MODEL', data='data',
                  rank=8, iters=50, batch_size=1, learning_rate=1e-4,
                  num_layers=16, adapter_path='adapters-smoke', save_every=50)
result = run_training(cfg, log_to='results/smoke_training.log')
print('loss_history:', result.loss_history)
print('final_loss:', result.final_loss, '| wall:', round(result.wall_seconds, 1), 's')
"

echo "== 5. 基础 vs LoRA 同评测集对比（ch07 30 条工单评测集）=="
PYTHONPATH=src $PY -m lora_lab.eval_compare \
  --base-model "$SMOKE_MODEL" \
  --adapter adapters-smoke \
  --max-tokens 256

echo "冒烟完成。结果见 results/<时间戳>/comparison.json"
