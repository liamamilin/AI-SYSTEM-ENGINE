"""Verify thinking behavior via Ollama native API (think on/off) + usage."""
import json
import os
import urllib.request

BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
MODEL = os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")


def call(messages, think=None, options=None):
    body = {"model": MODEL, "messages": messages, "stream": False}
    if think is not None:
        body["think"] = think
    if options:
        body["options"] = options
    req = urllib.request.Request(
        f"{BASE}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def main():
    # 1) default (thinking on, native API surfaces it)
    r = call([{"role": "user", "content": "推荐一个周末活动"}], options={"num_predict": 200})
    m = r["message"]
    print("default: think len:", len(m.get("thinking") or ""), "content len:", len((m.get("content") or "")))
    print("default content:", repr((m.get("content") or "")[:100]))

    # 2) think=false
    r2 = call([{"role": "user", "content": "推荐一个周末活动"}], think=False, options={"num_predict": 200})
    m2 = r2["message"]
    print("think=False: think len:", len(m2.get("thinking") or ""), "content len:", len((m2.get("content") or "")))
    print("think=False content:", repr((m2.get("content") or "")[:100]))

    # 3) truncation with think=False and small budget
    r3 = call([{"role": "user", "content": "写一段500字的产品介绍"}], think=False, options={"num_predict": 30})
    m3 = r3["message"]
    print("trunc think=False: content len:", len(m3.get("content") or ""), "done_reason:", r3.get("done_reason"))
    print("trunc content:", repr((m3.get("content") or "")[:80]))

    # 4) temperature via native options
    outs = []
    for _ in range(5):
        r4 = call(
            [{"role": "user", "content": "用不超过20个字点评远程办公"}],
            think=False,
            options={"temperature": 1.0, "num_predict": 100},
        )
        outs.append((r4["message"].get("content") or "").strip())
    print("temp=1(think off) distinct:", len(set(outs)), [o[:15] for o in outs])

    outs = []
    for _ in range(5):
        r5 = call(
            [{"role": "user", "content": "用不超过20个字点评远程办公"}],
            think=False,
            options={"temperature": 0, "num_predict": 100},
        )
        outs.append((r5["message"].get("content") or "").strip())
    print("temp=0(think off) distinct:", len(set(outs)), [o[:15] for o in outs])


if __name__ == "__main__":
    main()
