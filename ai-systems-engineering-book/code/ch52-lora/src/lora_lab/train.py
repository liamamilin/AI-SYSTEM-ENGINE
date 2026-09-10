"""mlx_lm lora 训练封装：参数映射（r/alpha/iters/lr/底座）+ dry-run + 真实训练。

章节锚点（ch52 正文 Mac 路线）：
    python -m mlx_lm lora --train --model <底座> \
      --data train.jsonl --epochs 3 --batch-size 1 --learning-rate 1e-4 \
      --num-layers 16        # 只训后 16 层的适配器（显存再省）
参数因果（正文）：
    rank    r       = 适配容量（简单行为 8–16，复杂 32–64）
    alpha   α       = 缩放因子，有效学习率 ~(α/r)，惯例 α=2r 起步
    targets/覆盖     = num_layers 控制适配器作用于后 N 层（MLX 默认覆盖 attention+FFN 线性层）
    底座            = 4bit 量化 repo（QLoRA 思想：冻结权重本身 4bit）

与已安装 mlx-lm（0.31.3，见 LAST_TESTED.md）CLI 的映射（章节命令是旧版语法）：
  - r/α 不再是 CLI 开关，经 `-c config.yaml` 的 lora_parameters 传入；
    MLX 的 scale 是低秩更新的直接乘子 h = Wx + scale·B(Ax)，
    与章节公式 h = Wx + (α/r)·B(Ax) 对照：scale = α/r（α=2r → scale=2.0）；
  - `--data` 接收目录（含 train.jsonl / valid.jsonl）而非单个文件；
  - 无 `--epochs`：iters = epochs × steps_per_epoch（steps_per_epoch = ceil(n_train/batch)）；
  - `--mask-prompt`：ch51 语义——仅 assistant 段参与 loss。

职责边界：本模块不发明训练逻辑，只做——
  1) TrainConfig -> mlx_lm CLI argv 的显式映射（纯函数，可被测试断言）；
  2) dry-run：只打印命令不执行（成本前置可见）；
  3) 真实训练：subprocess 运行并解析 "Iter N: Train loss ..." 流水。
"""

from __future__ import annotations

import math
import re
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ITER_LOSS_RE = re.compile(r"Iter\s+(\d+):\s+Train loss ([0-9.]+)")
# mlx_lm lora 实际支持的 CLI 开关（与安装版本核对，见 LAST_TESTED.md）
VALID_FLAGS = frozenset(
    {
        "--train",
        "--model",
        "--data",
        "--fine-tune-type",
        "--num-layers",
        "--batch-size",
        "--iters",
        "--val-batches",
        "--learning-rate",
        "--adapter-path",
        "--save-every",
        "--mask-prompt",
        "--seed",
        "--max-seq-length",
        "--steps-per-report",
        "--steps-per-eval",
        "-c",
    }
)

LORA_CONFIG_FILENAME = "lora_config.yaml"


@dataclass
class TrainConfig:
    model: str
    data: str  # 目录：含 train.jsonl（可选 valid.jsonl），与 mlx-lm 约定一致
    rank: int = 8
    alpha: int | None = None  # None -> 2*rank（章节惯例 α=2r 起步）
    num_layers: int = 16
    iters: int | None = None
    epochs: int = 3  # iters 未给出时换算：iters = epochs * ceil(n_train/batch)
    batch_size: int = 1
    learning_rate: float = 1e-4
    adapter_path: str | None = None  # 输出目录（默认 mlx_lm 写 ./adapters）
    save_every: int | None = None
    mask_prompt: bool = True  # ch51：仅 assistant 段参与 loss（掩码语义）
    seed: int = 42
    fine_tune_type: str = "lora"

    def resolved_alpha(self) -> int:
        return self.alpha if self.alpha is not None else 2 * self.rank

    def lora_scale(self) -> float:
        """MLX lora_parameters.scale = α/r（正文前向公式 h = Wx + (α/r)·B(Ax)）。"""
        return self.resolved_alpha() / self.rank

    def lora_config_yaml(self) -> dict:
        return {
            "lora_parameters": {
                "rank": self.rank,
                "dropout": 0.0,
                "scale": round(self.lora_scale(), 6),
            }
        }

    def validate(self) -> None:
        if not self.model:
            raise ValueError("model (base) is required")
        if not self.data:
            raise ValueError("data (directory with train.jsonl) is required")
        if self.rank < 1:
            raise ValueError(f"rank must be >= 1, got {self.rank}")
        if self.resolved_alpha() < 1:
            raise ValueError(f"alpha must be >= 1, got {self.resolved_alpha()}")
        if self.num_layers < 1:
            raise ValueError(f"num_layers must be >= 1, got {self.num_layers}")
        if self.iters is not None and self.iters < 1:
            raise ValueError(f"iters must be >= 1, got {self.iters}")
        if self.epochs < 1:
            raise ValueError(f"epochs must be >= 1, got {self.epochs}")
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be > 0, got {self.learning_rate}")
        if self.fine_tune_type != "lora":
            raise ValueError(f"only fine_tune_type='lora' is supported here, got {self.fine_tune_type!r}")
        # α/r 比值是有效学习率（案例二：α=8, r=32 -> 缩放 0.25 的静默失败）
        ratio = self.lora_scale()
        if ratio < 1:
            raise ValueError(
                f"alpha/rank = {ratio:.2f} < 1: effective learning signal too weak "
                "(chapter convention: alpha = 2 * rank)"
            )


def count_train_examples(data_dir: str | Path) -> int:
    """统计 data 目录下 train.jsonl 的条数（epochs->iters 换算用）。"""
    path = Path(data_dir) / "train.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"train.jsonl not found under data dir: {data_dir}")
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def steps_per_epoch(config: TrainConfig) -> int:
    return max(1, math.ceil(count_train_examples(config.data) / config.batch_size))


def resolved_iters(config: TrainConfig) -> int:
    """iters 显式给定则用之；否则 epochs 换算。"""
    return config.iters if config.iters is not None else config.epochs * steps_per_epoch(config)


def render_lora_config_yaml(config: TrainConfig) -> str:
    """YAML 文本（供 -c 传入 mlx_lm；含 rank/scale/dropout，训练时与命令一起留档）。"""
    params = config.lora_config_yaml()["lora_parameters"]
    return (
        "lora_parameters:\n"
        f"  rank: {params['rank']}\n"
        f"  dropout: {params['dropout']}\n"
        f"  scale: {params['scale']}\n"
    )


def write_lora_config(config: TrainConfig, path: str | Path | None = None) -> Path:
    """把 rank/alpha 配置写成 YAML（默认写到 adapter_path 目录，随 adapter 留档）。"""
    if path is not None:
        out = Path(path)
    elif config.adapter_path:
        out = Path(config.adapter_path) / LORA_CONFIG_FILENAME
    else:
        out = Path(tempfile.mkdtemp(prefix="lora-lab-")) / LORA_CONFIG_FILENAME
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_lora_config_yaml(config), encoding="utf-8")
    return out


def build_command(
    config: TrainConfig, *, python: str | None = None, config_yaml_path: str | None = None
) -> list[str]:
    """TrainConfig -> `python -m mlx_lm lora --train ...` argv（纯函数，可断言）。"""
    config.validate()
    argv = [python or sys.executable, "-m", "mlx_lm", "lora", "--train"]
    argv += ["--model", config.model]
    argv += ["--data", config.data]
    argv += ["--fine-tune-type", config.fine_tune_type]
    argv += ["--num-layers", str(config.num_layers)]
    argv += ["--batch-size", str(config.batch_size)]
    argv += ["--iters", str(resolved_iters(config))]
    argv += ["--learning-rate", str(config.learning_rate)]
    if config.mask_prompt:
        argv += ["--mask-prompt"]
    argv += ["--seed", str(config.seed)]
    if config.adapter_path:
        argv += ["--adapter-path", config.adapter_path]
    if config.save_every is not None:
        argv += ["--save-every", str(config.save_every)]
    yaml_path = config_yaml_path or write_lora_config(config)
    argv += ["-c", str(yaml_path)]
    unknown = {a for a in argv if a.startswith("--")} - VALID_FLAGS
    if unknown:
        raise ValueError(f"flags not accepted by mlx_lm lora: {sorted(unknown)}")
    return argv


def command_str(argv: list[str]) -> str:
    return shlex.join(argv)


def dry_run(config: TrainConfig, *, print_cmd: bool = True) -> str:
    """打印训练命令但不执行（成本前置可见；返回命令字符串）。"""
    yaml_path = write_lora_config(config)
    argv = build_command(config, config_yaml_path=str(yaml_path))
    cmd = command_str(argv)
    if print_cmd:
        print(f"[dry-run] {cmd}")
    return cmd


@dataclass
class TrainingResult:
    loss_history: list[tuple[int, float]] = field(default_factory=list)
    final_loss: float | None = None
    wall_seconds: float = 0.0
    config_yaml: str | None = None


def parse_loss_line(line: str) -> tuple[int, float] | None:
    m = ITER_LOSS_RE.search(line)
    return (int(m.group(1)), float(m.group(2))) if m else None


def run_training(
    config: TrainConfig,
    *,
    python: str | None = None,
    log_to: Path | None = None,
) -> TrainingResult:
    """真实执行训练，流式解析 train loss；非零退出码抛 RuntimeError。"""
    yaml_path = write_lora_config(config)
    argv = build_command(config, python=python, config_yaml_path=str(yaml_path))
    log_f = open(log_to, "w", encoding="utf-8") if log_to else None
    result = TrainingResult(config_yaml=str(yaml_path))
    t0 = time.perf_counter()
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:  # type: ignore[union-attr]
            if log_f:
                log_f.write(line)
                log_f.flush()
            parsed = parse_loss_line(line)
            if parsed:
                result.loss_history.append(parsed)
            if line.strip():
                print(line.rstrip(), flush=True)
        proc.wait()
    finally:
        result.wall_seconds = time.perf_counter() - t0
        if log_f:
            log_f.close()
    if proc.returncode != 0:
        raise RuntimeError(f"training failed (exit={proc.returncode}): {command_str(argv)}")
    result.final_loss = result.loss_history[-1][1] if result.loss_history else None
    return result
