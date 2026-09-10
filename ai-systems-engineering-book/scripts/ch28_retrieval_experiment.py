"""Ch28 experiment: BM25 vs embedding vs hybrid retrieval on a toy corpus.

Pure-Python BM25 + Ollama embeddings. 8 docs, 6 queries with known relevant doc.
Reports Recall@2 and MRR. Local, fast, no external deps beyond urllib.
"""

import json
import math
import os
import re
import urllib.request

BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")  # Ollama embeddings

DOCS = {
    "d1": "退款流程：订单签收后7天内可申请退款，进入订单详情页点击申请退款，1-3个工作日原路退回。",
    "d2": "物流查询：在订单详情页可查看实时物流轨迹，包裹由顺丰承运，一般2-4天送达。",
    "d3": "发票开具：支持电子普通发票和增值税专用发票，下单时可选择，也可在订单完成后补开。",
    "d4": "会员积分：每消费1元累计1积分，积分可兑换优惠券或礼品，有效期为获得之日起12个月。",
    "d5": "退换货政策：质量问题15天内可退货，非质量问题签收后7天内可换同款，需保持包装完好。",
    "d6": "优惠券使用：结算页选择可用优惠券，每单限用一张，优惠券不与积分抵扣叠加使用。",
    "d7": "配送范围：偏远地区（新疆、西藏等）可能延长至7天，且需加收运费，下单前会提示。",
    "d8": "价保规则：签收后15天内降价可申请差价补偿，需提供降价凭证，每个订单仅一次。",
}

QUERIES = [
    ("q1", "怎么申请退款", ["d1"]),
    ("q2", "货到哪了怎么查", ["d2"]),
    ("q3", "开发票", ["d3"]),
    ("q4", "降价了能补差价吗", ["d8"]),
    ("q5", "质量问题退货期限", ["d5"]),
    ("q6", "优惠券能和积分一起用吗", ["d6"]),
]

TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    # naive char-bigram for Chinese + words for latin (demo-grade, deterministic)
    toks = []
    han = re.findall(r"[\u4e00-\u9fff]+", text)
    for h in han:
        toks += [h[i:i+2] for i in range(len(h)-1)]
    toks += re.findall(r"[a-zA-Z0-9]+", text)
    return toks


class BM25:
    def __init__(self, docs: dict[str, str], k1=1.5, b=0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.dts = {i: tokenize(d) for i, d in docs.items()}
        self.dl = {i: len(t) for i, t in self.dts.items()}
        self.avgdl = sum(self.dl.values()) / len(docs)
        self.df: dict[str, int] = {}
        for toks in self.dts.values():
            for t in set(toks):
                self.df[t] = self.df.get(t, 0) + 1

    def score(self, query: str, doc_id: str) -> float:
        q = tokenize(query)
        toks, dl, s = self.dts[doc_id], self.dl[doc_id], 0.0
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        N = len(self.docs)
        for t in q:
            if t not in self.df:
                continue
            idf = math.log((N - self.df[t] + 0.5) / (self.df[t] + 0.5) + 1)
            f = tf.get(t, 0)
            s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def rank(self, query: str) -> list[str]:
        return sorted(self.docs, key=lambda i: -self.score(query, i))


def embed(text: str) -> list[float]:
    body = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
    req = urllib.request.Request(f"{BASE}/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["embeddings"][0]


def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x*x for x in a)), math.sqrt(sum(x*x for x in b))
    return dot / (na * nb + 1e-9)


def mrr_and_recall(rankings: dict[str, list[str]], relevant: dict[str, list[str]], k=2):
    recalls, rrs = [], []
    for q, rel in relevant.items():
        r = rankings[q]
        recalls.append(1.0 if any(d in rel for d in r[:k]) else 0.0)
        rr = 0.0
        for i, d in enumerate(r, 1):
            if d in rel:
                rr = 1.0 / i
                break
        rrs.append(rr)
    return sum(recalls)/len(recalls), sum(rrs)/len(rrs)


def main():
    bm25 = BM25(DOCS)
    emb = {i: embed(d) for i, d in DOCS.items()}

    def dense_rank(q):
        qe = embed(q)
        return sorted(DOCS, key=lambda i: -cosine(qe, emb[i]))

    def hybrid_rank(q, alpha=0.6):
        b = bm25.rank(q)
        d = dense_rank(q)
        bs = {doc: (len(b) - b.index(doc)) / len(b) for doc in b}
        ds = {doc: (len(d) - d.index(doc)) / len(d) for doc in d}
        return sorted(DOCS, key=lambda i: -(alpha * bs[i] + (1 - alpha) * ds[i]))

    rel = {q: r for q, _, r in QUERIES}
    for name, fn in [("BM25", lambda q: bm25.rank(q)), ("dense", dense_rank), ("hybrid", hybrid_rank)]:
        rankings = {q: fn(q) for q, _, _ in QUERIES}
        r2, mrr = mrr_and_recall(rankings, rel, k=2)
        print(f"{name:8s} Recall@2={r2:.2f}  MRR={mrr:.2f}")
    # show one failure case: q4 (价保) — lexical overlap is weak ("补差价" vs "价保/差价补偿")
    print("BM25 top2 for '降价了能补差价吗':", bm25.rank("降价了能补差价吗")[:2])


if __name__ == "__main__":
    main()
