"""Ch53 DPO 最小实验：TRL DPOTrainer + 0.5B 模型 + ch54 衍生偏好对

流程：
  1. gen_pairs：用 FP16 服务端模型为 30 个种子生成"敷衍回复"作 rejected
     （chosen 来自 ch54-synthetic.jsonl 的高分回复——差距清晰纪律）
  2. train：TRL DPOTrainer（Qwen2.5-0.5B-Instruct），测 chosen_logps/rewards/margins
  3. 对比：训练前后模型对同批 prompt 的 chosen-rejected 倾向

用法：
  python3 ch53_dpo_exp.py gen-pairs --base-url http://localhost:8000/v1 \
      --model Qwen/Qwen2.5-7B-Instruct --seeds ch54_seeds.json \
      --chosen ch54_chosen.jsonl --out ch53_pairs.jsonl
  python3 ch53_dpo_exp.py train --pairs ch53_pairs.jsonl --out ch53_dpo_results.json
"""
import argparse
import json
import time
from datetime import datetime, timezone

import httpx

LAZY_PROMPT = """写一个敷衍的客服回复（用于对比训练的反例）：只有空洞道歉，不解决任何问题，
不给具体步骤，不给时限，不超过 60 字。

用户工单：{seed}
"""


def cmd_gen_pairs(args):
    seeds = json.loads(open(args.seeds, encoding="utf-8").read())["seeds"]
    chosen = {}
    for l in open(args.chosen, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            chosen.setdefault(r["seed_id"], r["reply"])

    def gen_lazy(seed_texts):
        if args.base_url == "offline":
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            tok = AutoTokenizer.from_pretrained(args.model)
            m = AutoModelForCausalLM.from_pretrained(args.model, dtype="bfloat16", device_map="cuda:0")
            m.eval()
            outs = []
            for s in seed_texts:
                msgs = [{"role": "user", "content": LAZY_PROMPT.format(seed=s)}]
                text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                ids = tok(text, return_tensors="pt").to("cuda:0")
                with torch.no_grad():
                    o = m.generate(**ids, max_new_tokens=150, do_sample=True, temperature=0.9,
                                   top_p=0.9, pad_token_id=tok.eos_token_id)
                outs.append(tok.decode(o[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip())
            return outs
        outs = []
        with httpx.Client(timeout=90) as client:
            for s in seed_texts:
                r = client.post(f"{args.base_url}/chat/completions", json={
                    "model": args.model,
                    "messages": [{"role": "user", "content": LAZY_PROMPT.format(seed=s)}],
                    "max_tokens": 300, "temperature": 0.7})
                outs.append(r.json()["choices"][0]["message"]["content"].strip())
        return outs

    seed_texts = [s["input"] for s in seeds if s["id"] in chosen]
    seed_ids = [s["id"] for s in seeds if s["id"] in chosen]
    lazy_replies = gen_lazy(seed_texts)
    pairs = []
    for sid, seed_text, rej in zip(seed_ids, seed_texts, lazy_replies):
        if len(rej) < 10 or rej == chosen[sid]:
            continue
        pairs.append({"id": sid, "prompt": seed_text,
                      "chosen": chosen[sid], "rejected": rej})
    with open(args.out, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"pairs={len(pairs)} → {args.out}")


def cmd_train(args):
    from datasets import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOConfig, DPOTrainer

    pairs = [json.loads(l) for l in open(args.pairs, encoding="utf-8") if l.strip()]
    model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="bfloat16", device_map="cuda:0")
    ref = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="bfloat16", device_map="cuda:0")

    ds = Dataset.from_list([
        {"prompt": p["prompt"], "chosen": p["chosen"], "rejected": p["rejected"]}
        for p in pairs])
    cfg = DPOConfig(output_dir="/root/autodl-tmp/ch53_dpo_ckpt", beta=0.1,
                    per_device_train_batch_size=2, gradient_accumulation_steps=4,
                    num_train_epochs=3, learning_rate=5e-6, logging_steps=5,
                    report_to=[], save_strategy="no", lr_scheduler_type="constant")
    trainer = DPOTrainer(model=model, ref_model=ref, args=cfg,
                         train_dataset=ds, processing_class=tok)
    t0 = time.time()
    trainer.train()
    wall = time.time() - t0
    hist = [[h.get("step"), round(h.get("rewards/margins", 0), 4), round(h.get("loss", 0), 4)]
            for h in trainer.state.log_history if "loss" in h]
    metrics = {
        "model": model_name, "pairs": len(pairs), "epochs": cfg.num_train_epochs,
        "beta": cfg.beta, "wall_seconds": round(wall, 1),
        "final_loss": hist[-1][2] if hist else None,
        "final_margin": hist[-1][1] if hist else None,
        "log": hist,
        "peak_vram_gb": round(__import__("torch").cuda.max_memory_allocated() / 1024**3, 2),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(metrics, ensure_ascii=False, indent=1))
    with open(args.out, "w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen-pairs")
    g.add_argument("--base-url", default="http://localhost:8000/v1")
    g.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    g.add_argument("--seeds", default="/root/autodl-tmp/ch54_seeds.json")
    g.add_argument("--chosen", default="/root/autodl-tmp/ch54_chosen.jsonl")
    g.add_argument("--out", default="/root/autodl-tmp/ch53_pairs.jsonl")
    t = sub.add_parser("train")
    t.add_argument("--pairs", default="/root/autodl-tmp/ch53_pairs.jsonl")
    t.add_argument("--out", default="/root/autodl-tmp/ch53_dpo_results.json")
    args = ap.parse_args()
    {"gen-pairs": cmd_gen_pairs, "train": cmd_train}[args.cmd](args)
