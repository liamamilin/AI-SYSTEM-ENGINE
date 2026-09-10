"""data_prep 测试：chat JSONL schema 校验 / 配比 / 切分（纯 mock，不依赖模型）。"""

from __future__ import annotations

import json

import pytest

from lora_lab.data_prep import (
    DataFormatError,
    check_mix_ratio,
    load_records,
    mix_ratio,
    prepare,
    split_records,
    validate_record,
    write_jsonl,
)


def make_record(
    user: str = "耳机有杂音想退货",
    assistant: str = '{"category": "refund", "needs_human": false}',
    kind: str | None = None,
    system: str | None = "你是工单分类助手",
) -> dict:
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    messages.append({"role": "assistant", "content": assistant})
    record: dict = {"messages": messages}
    if kind:
        record["kind"] = kind
    return record


class TestValidateRecord:
    def test_valid_record_normalized(self):
        rec = validate_record(make_record())
        assert rec["kind"] == "task"  # 默认 task
        assert len(rec["messages"]) == 3

    def test_missing_messages_field(self):
        with pytest.raises(DataFormatError, match="messages"):
            validate_record({"prompt": "x"})

    def test_invalid_role(self):
        rec = make_record()
        rec["messages"][1]["role"] = "customer"
        with pytest.raises(DataFormatError, match="invalid role"):
            validate_record(rec)

    def test_empty_content(self):
        rec = make_record()
        rec["messages"][2]["content"] = "  "
        with pytest.raises(DataFormatError, match="non-empty"):
            validate_record(rec)

    def test_assistant_before_user_rejected(self):
        rec = {
            "messages": [
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "hello"},
            ]
        }
        with pytest.raises(DataFormatError, match="assistant before any user"):
            validate_record(rec)

    def test_last_message_must_be_assistant(self):
        rec = make_record()
        rec["messages"] = rec["messages"][:-1]
        with pytest.raises(DataFormatError, match="assistant segment"):
            validate_record(rec)

    def test_invalid_kind(self):
        with pytest.raises(DataFormatError, match="kind"):
            validate_record(make_record(kind="style"))

    def test_error_contains_line_number(self):
        with pytest.raises(DataFormatError, match=r"line 7"):
            validate_record({"no": "messages"}, index=6)


class TestLoadRecords:
    def test_load_and_validate(self, tmp_path):
        path = tmp_path / "data.jsonl"
        write_jsonl([make_record(), make_record(user="订单不想要了", kind="general")], path)
        records = load_records(path)
        assert len(records) == 2
        assert records[1]["kind"] == "general"

    def test_invalid_json_line_raises(self, tmp_path):
        good = make_record()
        path = tmp_path / "bad.jsonl"
        path.write_text(
            json.dumps(good, ensure_ascii=False) + "\nnot json\n", encoding="utf-8"
        )
        with pytest.raises(DataFormatError, match="line 2: invalid JSON"):
            load_records(path)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_records(tmp_path / "nope.jsonl")

    def test_empty_file_raises(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("\n\n", encoding="utf-8")
        with pytest.raises(DataFormatError, match="no valid records"):
            load_records(path)


class TestMixRatio:
    def test_counts_and_ratio(self):
        records = [make_record() for _ in range(8)] + [
            make_record(user=f"g{i}", kind="general") for i in range(2)
        ]
        stats = mix_ratio(records)
        assert stats["task"] == 8
        assert stats["general"] == 2
        assert stats["general_ratio"] == pytest.approx(0.2)

    def test_gate_passes_at_floor(self):
        records = [make_record() for _ in range(9)] + [make_record(kind="general")]
        check_mix_ratio(records, min_general_ratio=0.1)  # 不抛错

    def test_gate_rejects_below_floor(self):
        records = [make_record() for _ in range(10)]
        with pytest.raises(DataFormatError, match="mix ratio gate failed"):
            check_mix_ratio(records, min_general_ratio=0.1)


class TestSplit:
    def test_deterministic_same_seed(self):
        records = [make_record(user=f"q{i}") for i in range(20)]
        t1, v1 = split_records(records, val_ratio=0.2, seed=42)
        t2, v2 = split_records(records, val_ratio=0.2, seed=42)
        assert [r["messages"][1]["content"] for r in v1] == [r["messages"][1]["content"] for r in v2]
        assert len(v1) == len(v2) == 4  # round(20*0.2)
        assert len(t1) == len(t2) == 16

    def test_no_overlap_and_full_coverage(self):
        records = [make_record(user=f"q{i}") for i in range(15)]
        train, val = split_records(records, val_ratio=0.2, seed=42)
        assert len(train) + len(val) == 15
        users = [r["messages"][-2]["content"] for r in train + val]
        assert len(set(users)) == 15

    def test_single_record_goes_to_train(self):
        records = [make_record()]
        train, val = split_records(records, val_ratio=0.2, seed=42)
        assert len(train) == 1 and len(val) == 0

    def test_invalid_val_ratio(self):
        with pytest.raises(ValueError):
            split_records([make_record()], val_ratio=1.0)


class TestPrepareEndToEnd:
    def test_prepare_writes_train_val(self, tmp_path):
        src = tmp_path / "raw.jsonl"
        records = [make_record(user=f"问题{i}") for i in range(9)] + [
            make_record(user="通用问题", kind="general")
        ]
        src.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
        summary = prepare(src, tmp_path / "out", val_ratio=0.2, seed=42, min_general_ratio=0.1)
        assert summary["train"] == 8
        assert summary["val"] == 2
        train = load_records(tmp_path / "out" / "train.jsonl")
        val = load_records(tmp_path / "out" / "valid.jsonl")
        assert len(train) + len(val) == 10
        train_users = {r["messages"][-2]["content"] for r in train}
        val_users = {r["messages"][-2]["content"] for r in val}
        assert not train_users & val_users  # 交叉去重（ch51 三问之一）
