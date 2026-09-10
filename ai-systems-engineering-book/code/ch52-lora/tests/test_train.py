"""train.py 测试：参数映射 / dry-run / loss 解析（全部 mock，不触发真实训练）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lora_lab.train import (
    TrainConfig,
    build_command,
    count_train_examples,
    dry_run,
    parse_loss_line,
    render_lora_config_yaml,
    resolved_iters,
    run_training,
    steps_per_epoch,
    write_lora_config,
)


def make_data_dir(tmp_path: Path, n_train: int = 10, n_valid: int = 2) -> Path:
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    record = {
        "messages": [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "u"},
            {"role": "assistant", "content": "a"},
        ]
    }
    with open(d / "train.jsonl", "w", encoding="utf-8") as f:
        for i in range(n_train):
            f.write(json.dumps({**record, "messages": record["messages"]}, ensure_ascii=False) + "\n")
    if n_valid:
        with open(d / "valid.jsonl", "w", encoding="utf-8") as f:
            for i in range(n_valid):
                f.write(json.dumps({**record, "messages": record["messages"]}, ensure_ascii=False) + "\n")
    return d


def make_config(tmp_path: Path | None = None, **overrides) -> TrainConfig:
    defaults = dict(
        model="mlx-community/Qwen2.5-0.5B-Instruct-4bit",
        data="data",
        rank=8,
        num_layers=16,
        iters=50,
        epochs=3,
        batch_size=1,
        learning_rate=1e-4,
        adapter_path="adapters-smoke",
        save_every=50,
    )
    defaults.update(overrides)
    return TrainConfig(**defaults)


class TestParamMapping:
    def test_alpha_defaults_to_2r(self):
        cfg = make_config(rank=8)
        assert cfg.resolved_alpha() == 16  # 惯例 α=2r
        assert cfg.lora_scale() == 2.0

    def test_alpha_explicit(self):
        cfg = make_config(rank=32, alpha=64)
        assert cfg.resolved_alpha() == 64

    def test_lora_config_yaml_maps_rank_alpha_to_scale(self):
        # MLX 的 scale 是直接乘子：scale = α/r（α=2r → 2.0）
        yaml_text = render_lora_config_yaml(make_config(rank=16))
        assert "rank: 16" in yaml_text
        assert "scale: 2.0" in yaml_text

    def test_build_command_contains_all_params(self, tmp_path):
        cfg = make_config(data=str(make_data_dir(tmp_path)), rank=16)
        yaml_path = write_lora_config(cfg, path=tmp_path / "cfg.yaml")
        argv = build_command(cfg, config_yaml_path=str(yaml_path))
        text = " ".join(argv)
        assert "-m mlx_lm lora --train" in text
        assert "--model mlx-community/Qwen2.5-0.5B-Instruct-4bit" in text
        assert f"--data {tmp_path / 'data'}" in text
        assert "--fine-tune-type lora" in text
        assert "--num-layers 16" in text
        assert "--batch-size 1" in text
        assert "--learning-rate 0.0001" in text
        assert "--iters 50" in text
        assert "--save-every 50" in text
        assert "--adapter-path adapters" in text
        assert "--mask-prompt" in argv  # ch51：仅 assistant 段参与 loss
        assert "--seed 42" in text
        assert "-c" in argv and str(yaml_path) in argv

    def test_epochs_converted_to_iters(self, tmp_path):
        data = make_data_dir(tmp_path, n_train=10)
        cfg = make_config(data=str(data), iters=None, epochs=3, batch_size=1)
        assert count_train_examples(data) == 10
        assert steps_per_epoch(cfg) == 10
        assert resolved_iters(cfg) == 30  # epochs × ceil(n/batch)
        argv = build_command(cfg)
        assert "--iters 30" in " ".join(argv)

    def test_iters_takes_precedence(self, tmp_path):
        cfg = make_config(data=str(make_data_dir(tmp_path)), iters=50, epochs=3)
        assert resolved_iters(cfg) == 50

    def test_missing_train_jsonl_raises(self, tmp_path):
        cfg = make_config(data=str(tmp_path), iters=None, epochs=3)
        with pytest.raises(FileNotFoundError):
            resolved_iters(cfg)

    def test_chapter_baseline_command(self, tmp_path):
        # 章节主线：9B 底座 4bit + r=32/α=64 惯例 + 后 16 层
        cfg = make_config(model="mlx-community/Qwen3.5-9B-4bit", rank=32, alpha=64)
        yaml_text = render_lora_config_yaml(cfg)
        assert "rank: 32" in yaml_text and "scale: 2.0" in yaml_text

    def test_alpha_weaker_than_rank_rejected(self):
        # 章节案例二：α=8, r=32 -> 有效缩放 0.25 的静默失败，必须在构建命令前拦截
        with pytest.raises(ValueError, match="alpha/rank"):
            build_command(make_config(rank=32, alpha=8))

    def test_invalid_configs_raise(self):
        with pytest.raises(ValueError, match="rank"):
            build_command(make_config(rank=0))
        with pytest.raises(ValueError, match="learning_rate"):
            build_command(make_config(learning_rate=0))
        with pytest.raises(ValueError, match="fine_tune_type"):
            build_command(make_config(fine_tune_type="full"))
        with pytest.raises(ValueError, match="epochs"):
            build_command(make_config(epochs=0))

    def test_only_known_flags_used(self, tmp_path):
        cfg = make_config(data=str(make_data_dir(tmp_path)))
        write_lora_config(cfg, path=tmp_path / "cfg.yaml")
        from lora_lab.train import VALID_FLAGS

        argv = build_command(cfg, config_yaml_path=str(tmp_path / "cfg.yaml"))
        unknown = {a for a in argv if a.startswith("--")} - VALID_FLAGS
        assert not unknown


class TestDryRun:
    def test_dry_run_prints_command_without_executing(self, capsys, monkeypatch, tmp_path):
        called = []

        def boom(*a, **k):  # 任何 subprocess 使用都会让测试失败
            called.append(a)
            raise AssertionError("dry-run must not execute subprocess")

        monkeypatch.setattr("lora_lab.train.subprocess.Popen", boom)
        cfg = make_config(adapter_path=str(tmp_path / "adapters"))
        cmd = dry_run(cfg)
        out = capsys.readouterr().out
        assert out.startswith("[dry-run] ")
        assert "-m mlx_lm lora --train" in out
        assert "--iters 50" in out
        assert cmd == out.removeprefix("[dry-run] ").strip()
        assert not called
        # 配置随 adapter 留档
        assert (tmp_path / "adapters" / "lora_config.yaml").exists()


class TestRunTraining:
    class FakeProc:
        def __init__(self, lines, returncode=0):
            self.stdout = iter(lines)
            self.returncode = returncode

        def wait(self):
            return self.returncode

    def test_loss_history_parsed(self, monkeypatch, tmp_path):
        lines = [
            "Loading model...\n",
            "Iter 10: Train loss 1.842, It/sec 1.2, Tokens/sec 88.1\n",
            "Iter 20: Train loss 1.413, It/sec 1.3, Tokens/sec 91.0\n",
            "Iter 30: Train loss 0.977, It/sec 1.3, Tokens/sec 92.3\n",
        ]
        monkeypatch.setattr(
            "lora_lab.train.subprocess.Popen",
            lambda *a, **k: self.FakeProc(lines),
        )
        result = run_training(make_config(adapter_path=str(tmp_path / "adapters")))
        assert result.loss_history == [(10, 1.842), (20, 1.413), (30, 0.977)]
        assert result.final_loss == 0.977
        assert result.wall_seconds >= 0

    def test_nonzero_exit_raises(self, monkeypatch):
        monkeypatch.setattr(
            "lora_lab.train.subprocess.Popen",
            lambda *a, **k: self.FakeProc(["Iter 10: Train loss 2.0\n"], returncode=1),
        )
        with pytest.raises(RuntimeError, match="training failed"):
            run_training(make_config())

    def test_no_loss_lines_is_ok(self, monkeypatch):
        monkeypatch.setattr(
            "lora_lab.train.subprocess.Popen",
            lambda *a, **k: self.FakeProc(["nothing to see\n"]),
        )
        result = run_training(make_config())
        assert result.loss_history == []
        assert result.final_loss is None


class TestParseLossLine:
    def test_variants(self):
        assert parse_loss_line("Iter 5: Train loss 2.500, It/sec 1.0") == (5, 2.5)
        assert parse_loss_line("Iter 100: Train loss 0.0831, ...") == (100, 0.0831)
        assert parse_loss_line("no loss here") is None
