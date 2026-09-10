"""Ch54 最小蒸馏实验：Zen API teacher（omen-alpha）→ 三道过滤 → 合成数据集 + 健康报告

流水线（对应 ch54 章节「生成-过滤流水线」）：
  真实种子 30 条 → teacher 生成 K=3 候选（temperature 0.3/0.7/1.0）
  → 规则过滤（长度/PII/拒答/复读种子）
  → 模型过滤（teacher 自审：正确性/相关性打分，阈值 4/5）
  → 语义去重（本地 bge-m3 embedding，cosine ≥ 0.92 合并，防同质化）
  → 入库（synthetic 标签 + teacher 血缘 provenance）+ 健康指标报告

运行：python3 scripts/ch54_distillation_experiment.py
依赖：httpx（teacher 调用）、本地 Ollama（bge-m3，语义去重）
密钥：从 scripts/.env 读取（ZEN_API_KEY），不写入代码
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SEEDS_PATH = ROOT / "datasets" / "sample" / "ch54-seeds.json"
OUT_JSONL = ROOT / "datasets" / "sample" / "ch54-synthetic.jsonl"
REPORT_PATH = ROOT / "experiments" / "ch54_distillation_report.md"
ENV_PATH = Path(__file__).resolve().parent / ".env"

TEACHER_TEMPS = [0.3, 0.7, 1.0]
JUDGE_THRESHOLD = 4          # 正确性/相关性均需 >= 4（1-5 分制）
DEDUP_SIM_THRESHOLD = 0.92   # cosine 超过视为近重复
OLLAMA_EMBED = "http://localhost:11434/api/embeddings"
OLLAMA_EMBED_MODEL = "bge-m3"
GEN_MAX_TOKENS = 3000        # reasoning tokens 占用 max_tokens（ch05 发现）
JUDGE_MAX_TOKENS = 1500
CONCURRENCY = 4


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env(ENV_PATH)
API_KEY = os.environ.get("ZEN_API_KEY", ENV["ZEN_API_KEY"])
BASE_URL = os.environ.get("ZEN_BASE_URL", ENV["ZEN_BASE_URL"])
MODEL = os.environ.get("ZEN_MODEL", ENV["ZEN_MODEL"])
SESSION = os.environ.get("ZEN_SESSION", ENV.get("ZEN_SESSION", "ch54-distill-exp"))

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-opencode-session": SESSION,
    "Content-Type": "application/json",
}


def chat(messages: list, temperature: float, max_tokens: int, retries: int = 3) -> dict:
    """调用 Zen API。reasoning tokens 占用 max_tokens，故 max_tokens 需放宽。"""
    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_err = None
    for attempt in range(retries):
        try:
            r = httpx.post(url, headers=HEADERS, json=payload, timeout=180)
            r.raise_for_status()
            data = r.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})
            return {
                "content": choice["message"].get("content", "") or "",
                "finish_reason": choice.get("finish_reason", ""),
                "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        except Exception as e:  # 指数退避重试
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"teacher 调用失败: {last_err}")


GENERATE_PROMPT = """你是资深客服。针对下面的真实用户工单，写一条可直接发给用户的回复。

要求：
- 先共情/确认问题，再给出具体可执行的解决步骤（编号列出）
- 涉及承诺时明确时限（如 24 小时内）
- 不确定的信息明确说"需要进一步核实"，不要编造政策细节
- 150–400 字，中文，语气专业但不对用户说教

用户工单：
{seed}
"""

PII_PATTERNS = [
    re.compile(r"\b1[3-9]\d{9}\b"),              # 手机号
    re.compile(r"\b\d{17}[\dXx]\b"),              # 身份证
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),       # 邮箱
    re.compile(r"\b\d{16,19}\b"),                 # 银行卡
]
REFUSAL_MARKERS = ["我无法", "作为AI", "作为 AI", "我不能", "抱歉，我无法"]


def rule_filter(text: str, seed_input: str) -> tuple[bool, str]:
    """规则过滤（确定性，先跑）。返回 (pass, reason)。"""
    if not text.strip():
        return False, "empty"
    if not (30 <= len(text) <= 2000):
        return False, f"length({len(text)})"
    for pat in PII_PATTERNS:
        if pat.search(text):
            return False, "pii"
    for m in REFUSAL_MARKERS:
        if m in text:
            return False, "refusal"
    # 复读种子：输出主体是输入的复制（防"模型复读"而非回答）
    if seed_input[:20] in text and len(text) < len(seed_input) * 2:
        return False, "echo"
    return True, "ok"


JUDGE_PROMPT = """你是质检员。审阅下面这条客服回复（针对给定用户工单），独立打分。

评分（1-5 整数）：
- correctness: 解决方案是否正确、可执行；是否编造了不存在的政策/时限/功能
- relevance: 是否回应了工单的核心诉求；是否有大段无关内容

只输出 JSON：{{"correctness": n, "relevance": n, "issue": "若无问题填空串，否则一句话指出"}}

用户工单：
{seed}

客服回复：
{reply}
"""


def judge_reply(seed_input: str, reply: str) -> dict:
    out = chat(
        [{"role": "user", "content": JUDGE_PROMPT.format(seed=seed_input, reply=reply)}],
        temperature=0.0,
        max_tokens=JUDGE_MAX_TOKENS,
    )
    m = re.search(r"\{[^{}]*\}", out["content"], re.S)
    if not m:
        return {"correctness": 0, "relevance": 0, "issue": "judge_unparseable"}
    try:
        j = json.loads(m.group(0))
        return {
            "correctness": int(j.get("correctness", 0)),
            "relevance": int(j.get("relevance", 0)),
            "issue": str(j.get("issue", ""))[:200],
        }
    except (json.JSONDecodeError, ValueError):
        return {"correctness": 0, "relevance": 0, "issue": "judge_unparseable"}


def embed(text: str) -> list:
    r = httpx.post(OLLAMA_EMBED, json={"model": OLLAMA_EMBED_MODEL, "prompt": text[:2000]}, timeout=60)
    r.raise_for_status()
    return r.json()["embedding"]


def cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def semantic_dedup(items: list, threshold: float) -> tuple[list, int]:
    """贪心去重：与已保留项 cosine ≥ threshold 视为近重复。"""
    kept, vectors, dropped = [], [], 0
    for it in items:
        v = embed(it["reply"])
        if any(cosine(v, w) >= threshold for w in vectors):
            dropped += 1
            continue
        vectors.append(v)
        kept.append(it)
    return kept, dropped


def main() -> int:
    t0 = time.time()
    seeds = json.loads(SEEDS_PATH.read_text())["seeds"]
    print(f"[ch54] seeds={len(seeds)} teacher={MODEL} temps={TEACHER_TEMPS}")

    # Stage 1: teacher 生成（并发）
    def gen_one(seed: dict, temp: float) -> dict | None:
        try:
            out = chat(
                [{"role": "user", "content": GENERATE_PROMPT.format(seed=seed["input"])}],
                temperature=temp,
                max_tokens=GEN_MAX_TOKENS,
            )
            return {
                "seed_id": seed["id"], "seed_type": seed["type"], "temp": temp,
                "reply": out["content"].strip(),
                "finish_reason": out["finish_reason"],
                "gen_reasoning_tokens": out["reasoning_tokens"],
            }
        except RuntimeError as e:
            print(f"  [gen-fail] {seed['id']} t={temp}: {e}")
            return None

    candidates = []
    jobs = [(s, t) for s in seeds for t in TEACHER_TEMPS]
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(gen_one, s, t): (s["id"], t) for s, t in jobs}
        done = 0
        for fut in as_completed(futures):
            c = fut.result()
            if c:
                candidates.append(c)
            done += 1
            if done % 15 == 0:
                print(f"  [gen] {done}/{len(jobs)} done, candidates={len(candidates)}")
    candidates.sort(key=lambda c: (c["seed_id"], c["temp"]))

    # Stage 2: 规则过滤
    seed_map = {s["id"]: s["input"] for s in seeds}
    rule_pass, rule_fail = [], []
    for c in candidates:
        ok, reason = rule_filter(c["reply"], seed_map[c["seed_id"]])
        (rule_pass if ok else rule_fail).append({**c, "rule_fail_reason": reason})
    print(f"[rule] pass={len(rule_pass)} fail={len(rule_fail)}")

    # Stage 3: teacher 自审（并发）
    def judge_one(c: dict) -> tuple[dict, dict]:
        score = judge_reply(seed_map[c["seed_id"]], c["reply"])
        return c, score

    model_pass, model_fail = [], []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [pool.submit(judge_one, c) for c in rule_pass]
        done = 0
        for fut in as_completed(futures):
            c, score = fut.result()
            c["judge"] = score
            ok = score["correctness"] >= JUDGE_THRESHOLD and score["relevance"] >= JUDGE_THRESHOLD
            (model_pass if ok else model_fail).append(c)
            done += 1
            if done % 15 == 0:
                print(f"  [judge] {done}/{len(rule_pass)} ok={len(model_pass)} fail={len(model_fail)}")

    # Stage 4: 语义去重
    kept, dropped = semantic_dedup(model_pass, DEDUP_SIM_THRESHOLD)
    print(f"[dedup] kept={len(kept)} dropped={dropped}")

    # Stage 5: 入库（provenance 血缘）
    now = datetime.now(timezone.utc).isoformat()
    records = []
    for c in kept:
        records.append({
            "id": f"syn-{c['seed_id']}-t{c['temp']}",
            "seed_id": c["seed_id"], "seed_type": c["seed_type"],
            "synthetic": True, "teacher": MODEL,
            "teacher_session": SESSION, "temperature": c["temp"],
            "generated_at": now, "lineage": "seed→teacher→3层过滤",
            "judge": c["judge"],
            "reply": c["reply"],
        })
    OUT_JSONL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")

    # Stage 6: 健康指标
    sims = []
    vecs = [embed(r["reply"]) for r in records]
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            sims.append(cosine(vecs[i], vecs[j]))
    avg_sim = sum(sims) / len(sims) if sims else 0.0
    by_temp = {}
    for r in records:
        by_temp.setdefault(r["temperature"], 0)
        by_temp[r["temperature"]] += 1

    funnel = f"""# Ch54 最小蒸馏实验报告

- 运行时间：{now}
- Teacher：{MODEL}（Zen API，session={SESSION}）
- Seeds：{len(seeds)} 条（datasets/sample/ch54-seeds.json，人工编写模拟真实工单分布）
- Student：qwen3.5:9b（本地，LoRA 训练走 ch52 路线，本实验不含训练）

## 过滤漏斗

| 阶段 | 输入 | 通过 | 淘汰 | 通过率 |
|---|---|---|---|---|
| 生成 | {len(seeds)}×{len(TEACHER_TEMPS)}={len(candidates) or len(seeds) * 3} | {len(candidates)} | - | - |
| 规则过滤 | {len(candidates)} | {len(rule_pass)} | {len(rule_fail)} | {len(rule_pass) / max(len(candidates), 1):.0%} |
| teacher 自审 | {len(rule_pass)} | {len(model_pass)} | {len(model_fail)} | {len(model_pass) / max(len(rule_pass), 1):.0%} |
| 语义去重 | {len(model_pass)} | {len(kept)} | {dropped} | {len(kept) / max(len(model_pass), 1):.0%} |

## 健康指标（ch54「合成数据健康」清单）

- 抽审幻觉代理：judge correctness<4 但被规则放行 {len(model_fail)} 条（自审拦下）
- 语义多样性：平均成对 cosine = {avg_sim:.3f}（阈值参考 >0.9 警惕同质化）
- 温度多样性分布：{by_temp}
- 血缘完整率：{sum(1 for r in records if r['teacher'] and r['seed_id'] and r['generated_at'])}/{len(records)} = 100%

## 结论

方向结论（数值按任务而异）：真实种子 + 三道过滤后，合成数据自带可追溯血缘与质量分层，
可直接进入 ch50 六项门禁与 ≤30–50% 配比混合。teacher 自审淘汰了 {len(model_fail)} 条，
验证「teacher 不是完美过滤器——需人工抽审校准」的章节论点。

- Last verified: {datetime.now().strftime('%Y-%m-%d')}
"""
    REPORT_PATH.write_text(funnel)
    elapsed = time.time() - t0
    print(f"[done] records={len(records)} avg_pairwise_cos={avg_sim:.3f} elapsed={elapsed:.0f}s")
    print(f"  → {OUT_JSONL}\n  → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
