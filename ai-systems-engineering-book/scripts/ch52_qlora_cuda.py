"""Ch52 CUDA QLoRA 实测：NF4 显存账 + 训练吞吐（对照章节第 51/52 章显存账）

在 RTX 4080 SUPER 32GB 上：
  1. Qwen2.5-7B-Instruct 以 NF4(bitsandbytes 4bit) 加载 → 权重显存
  2. LoRA r=16 α=32（α=2r 惯例）挂 q/k/v/o/gate/up/down → 可训练参数占比
  3. 前向+反向 10 步（seq 512）→ torch.cuda.max_memory_allocated + steps/s
  4. 训练 20 步看 loss 下降

用法：python3 ch52_qlora_cuda.py --model Qwen/Qwen2.5-7B-Instruct --out /root/autodl-tmp/ch52_qlora_results.json
"""
import argparse
import gc
import json
import time
from datetime import datetime, timezone

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def fmt_gb(n):
    return round(n / 1024**3, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--train-file", default="/root/autodl-tmp/ch52_train.jsonl")
    ap.add_argument("--out", default="/root/autodl-tmp/ch52_qlora_results.json")
    ap.add_argument("--steps", type=int, default=20)
    args = ap.parse_args()

    results = {"meta": {"model": args.model,
                        "gpu": torch.cuda.get_device_name(0),
                        "vram_total_gb": fmt_gb(torch.cuda.get_device_properties(0).total_memory),
                        "ts": datetime.now(timezone.utc).isoformat()}}

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16)
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=bnb, device_map="cuda:0",
        torch_dtype=torch.bfloat16)
    tok = AutoTokenizer.from_pretrained(args.model)
    load_s = round(time.time() - t0, 1)
    torch.cuda.reset_peak_memory_stats()
    weights_gb = fmt_gb(torch.cuda.memory_allocated())
    print(f"[load] {load_s}s, weights={weights_gb}GB")

    # LoRA 挂载（ch52 参数惯例：α=2r；targets=attention+MLP 全量）
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    model = prepare_model_for_kbit_training(model)
    lcfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                      "gate_proj", "up_proj", "down_proj"],
                      task_type="CAUSAL_LM")
    model = get_peft_model(model, lcfg)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"[lora] trainable={trainable/1e6:.2f}M ({trainable/total:.3%})")
    model.print_trainable_parameters()

    # 数据：chat 格式 jsonl（与 ch52-lora data_prep 输出同构）
    rows = [json.loads(l) for l in open(args.train_file, encoding="utf-8") if l.strip()]

    def encode(rec):
        msgs = rec["messages"]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        return tok(text, add_special_tokens=False)["input_ids"][:512]

    pad_id = tok.pad_token_id or tok.eos_token_id

    def make_batch(recs):
        enc = [encode(r) for r in recs]
        maxlen = max(len(e) for e in enc)
        ids = torch.tensor([e + [pad_id] * (maxlen - len(e)) for e in enc], device="cuda:0")
        mask = (ids != pad_id).long()
        return ids, mask, ids.masked_fill(mask == 0, -100)

    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)

    # 训练循环（真实 loss 下降 + 吞吐）
    losses, t_start = [], time.time()
    peak = 0
    for step in range(args.steps):
        recs = [rows[(step * 2 + i) % len(rows)] for i in range(2)]
        input_ids, attention_mask, labels = make_batch(recs)
        out = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        out.loss.backward()
        opt.step()
        opt.zero_grad()
        losses.append(round(out.loss.item(), 4))
        peak = torch.cuda.max_memory_allocated()
        if step % 5 == 0:
            print(f"[step {step}] loss={losses[-1]} peak={fmt_gb(peak)}GB")
    train_s = time.time() - t_start

    results["qlora"] = {
        "load_seconds": load_s,
        "weights_gb_nf4": weights_gb,
        "peak_vram_gb": fmt_gb(peak),
        "trainable_params": trainable,
        "trainable_pct": round(trainable / total * 100, 3),
        "steps": args.steps,
        "batch_tokens": 0,
        "seconds": round(train_s, 1),
        "steps_per_s": round(args.steps / train_s, 2),
        "loss_first": losses[0],
        "loss_last": losses[-1],
        "loss_curve": losses,
    }
    print(json.dumps(results["qlora"], ensure_ascii=False, indent=1))
    with open(args.out, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"saved → {args.out}")


if __name__ == "__main__":
    main()
