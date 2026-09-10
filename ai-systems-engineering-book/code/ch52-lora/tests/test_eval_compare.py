"""eval_compare 测试：JSON 提取 / 判分 / 聚合 / 对比 delta（fake generator，不加载模型）。"""

from __future__ import annotations

import json

import pytest

from lora_lab.eval_compare import (
    aggregate,
    diff_metrics,
    extract_json,
    find_default_dataset,
    judge_case,
    load_dataset,
    resolve_adapter_dir,
    run_model,
    write_results,
)

GOOD = '{"category": "refund", "urgency": "low", "summary": "退货申请", "needs_human": false}'


class TestExtractJson:
    def test_plain_json(self):
        assert extract_json(GOOD)["category"] == "refund"

    def test_fenced_json(self):
        assert extract_json(f"```json\n{GOOD}\n```")["needs_human"] is False

    def test_json_with_prefix_junk(self):
        assert extract_json(f"好的，结果如下：{GOOD} 以上。")["category"] == "refund"

    def test_no_json_returns_none(self):
        assert extract_json("抱歉我不知道") is None

    def test_broken_json_returns_none(self):
        assert extract_json('{"category": "refund",') is None


class TestJudge:
    def _expected(self, category="refund", needs_human=False):
        return {"id": "t01", "expected": {"category": category, "needs_human": needs_human}}

    def test_correct(self):
        row = judge_case(GOOD, self._expected())
        assert row["schema_ok"] and row["category_ok"] and row["needs_human_ok"]

    def test_wrong_category(self):
        out = GOOD.replace('"refund"', '"logistics"')
        row = judge_case(out, self._expected())
        assert row["schema_ok"] and not row["category_ok"] and row["needs_human_ok"]

    def test_invalid_category_value_fails_schema_semantics(self):
        out = GOOD.replace('"refund"', '"shipping"')
        row = judge_case(out, self._expected())
        assert not row["category_ok"]

    def test_unparseable_fails_all(self):
        row = judge_case("我想帮你退货，请稍等", self._expected())
        assert not row["schema_ok"] and not row["category_ok"] and not row["needs_human_ok"]

    def test_non_bool_needs_human_fails(self):
        out = GOOD.replace('"needs_human": false', '"needs_human": "no"')
        row = judge_case(out, self._expected())
        assert not row["needs_human_ok"]


class TestAggregateAndDiff:
    def test_aggregate_rates(self):
        rows = [
            {"schema_ok": True, "category_ok": True, "needs_human_ok": True},
            {"schema_ok": True, "category_ok": False, "needs_human_ok": True},
            {"schema_ok": False, "category_ok": False, "needs_human_ok": False},
        ]
        m = aggregate(rows)
        assert m["n"] == 3
        assert m["schema_ok_rate"] == pytest.approx(2 / 3)
        assert m["category_accuracy"] == pytest.approx(1 / 3)
        assert m["needs_human_accuracy"] == pytest.approx(2 / 3)

    def test_aggregate_empty_raises(self):
        with pytest.raises(ValueError):
            aggregate([])

    def test_diff_metrics_lora_minus_base(self):
        base = {"schema_ok_rate": 0.9, "category_accuracy": 0.5, "needs_human_accuracy": 0.6}
        lora = {"schema_ok_rate": 1.0, "category_accuracy": 0.7, "needs_human_accuracy": 0.6}
        d = diff_metrics(base, lora)
        assert d == {"schema_ok_rate": 0.1, "category_accuracy": 0.2, "needs_human_accuracy": 0.0}


class TestRunModel:
    def test_fake_generator_scripted_outputs(self):
        cases = [
            {"id": "t01", "input": "耳机有杂音想退货", "expected": {"category": "refund", "needs_human": False}},
            {"id": "t02", "input": "快递三天没动", "expected": {"category": "logistics", "needs_human": False}},
        ]

        def gen(prompt: str) -> str:
            if "耳机" in prompt:
                return GOOD
            return "好的我来查一下物流。"  # 模拟基础模型不输出 JSON

        rows, metrics, _ = run_model(gen, cases)
        assert [r["id"] for r in rows] == ["t01", "t02"]
        assert metrics["schema_ok_rate"] == 0.5
        assert metrics["category_accuracy"] == 0.5
        assert metrics["needs_human_accuracy"] == 0.5
        assert rows[0]["output"] == GOOD

    def test_limit_cases(self):
        cases = [
            {"id": f"t{i:02d}", "input": f"问题{i}", "expected": {"category": "other", "needs_human": False}}
            for i in range(5)
        ]
        rows, metrics, _ = run_model(lambda p: GOOD, cases, max_cases=2)
        assert len(rows) == 2 and metrics["n"] == 2


class TestDatasetIO:
    def test_load_dataset_ch07_format(self, tmp_path):
        path = tmp_path / "dataset.jsonl"
        path.write_text(
            json.dumps({"id": "t01", "input": "x", "expected": {"category": "refund", "needs_human": False}},
                       ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cases = load_dataset(path)
        assert cases[0]["id"] == "t01"

    def test_load_dataset_missing_field_raises(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text('{"id": "t01", "input": "x"}\n', encoding="utf-8")
        with pytest.raises(ValueError, match="expected"):
            load_dataset(path)

    def test_load_dataset_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "nope.jsonl")

    def test_default_dataset_is_ch07_30_cases(self):
        # 复用 ch07 评测集：本仓库内应能定位到（找不到时报清晰错误）
        path = find_default_dataset()
        cases = load_dataset(path)
        assert len(cases) == 30


class TestResolveAdapterDir:
    def test_safetensors_file_maps_to_parent_dir(self, tmp_path):
        adapter_dir = tmp_path / "adapters-smoke"
        adapter_dir.mkdir()
        (adapter_dir / "adapters.safetensors").write_bytes(b"x")
        assert resolve_adapter_dir(str(adapter_dir / "0000050_adapters.safetensors")) == str(adapter_dir)

    def test_directory_passthrough(self, tmp_path):
        assert resolve_adapter_dir(str(tmp_path)) == str(tmp_path)


class TestWriteResults:
    def test_writes_results_and_comparison(self, tmp_path):
        base_rows = [{"id": "t01", "schema_ok": True, "category_ok": True, "needs_human_ok": True, "output": "x"}]
        lora_rows = [{"id": "t01", "schema_ok": True, "category_ok": False, "needs_human_ok": True, "output": "y"}]
        base_m = aggregate(base_rows)
        lora_m = aggregate(lora_rows)
        out = write_results(
            tmp_path / "results" / "t1",
            base_rows=base_rows,
            lora_rows=lora_rows,
            base_metrics=base_m,
            lora_metrics=lora_m,
            metadata={"base_model": "m", "adapter": None},
        )
        assert (out / "results.jsonl").exists()
        payload = json.loads((out / "comparison.json").read_text(encoding="utf-8"))
        assert payload["base_model"] == "m"
        assert payload["delta"]["category_accuracy"] == -1.0
        first = json.loads((out / "results.jsonl").read_text(encoding="utf-8").splitlines()[0])
        assert first["model"] == "base"
