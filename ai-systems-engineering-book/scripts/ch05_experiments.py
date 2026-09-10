"""Ch5 experiments v2: inspect usage, thinking tokens, sampling behavior."""
import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.environ.get("LLM_API_KEY", "ollama"),
)
MODEL = os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")


def full_call(messages, temperature=None, max_tokens=None):
    kw = {"model": MODEL, "messages": messages}
    if temperature is not None:
        kw["temperature"] = temperature
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    r = client.chat.completions.create(**kw)
    c = r.choices[0]
    usage = r.usage
    return c.message, c.finish_reason, usage


def main():
    # 1) inspect usage on a simple call
    msg, fr, usage = full_call([{"role": "user", "content": "推荐一个周末活动"}], max_tokens=200)
    print("finish_reason:", fr)
    print("usage:", usage)
    print("content repr (first 200):", repr((msg.content or "")[:200]))
    rc = getattr(msg, "reasoning_content", None)
    print("reasoning_content present:", rc is not None, "len:", len(rc or ""))

    # 2) temperature behavior with more samples, measure prompt/completion tokens
    outs = []
    for _ in range(5):
        msg, fr, u = full_call(
            [{"role": "user", "content": "用不超过20个字点评远程办公"}],
            temperature=1.0,
            max_tokens=200,
        )
        outs.append((msg.content or "").strip())
    print("temp=1 distinct:", len(set(outs)), "samples:", [o[:20] for o in outs])

    outs = []
    for _ in range(5):
        msg, fr, u = full_call(
            [{"role": "user", "content": "用不超过20个字点评远程办公"}],
            temperature=0,
            max_tokens=200,
        )
        outs.append((msg.content or "").strip())
    print("temp=0 distinct:", len(set(outs)), "samples:", [o[:20] for o in outs])

    # 3) truncation: small max_tokens, reasoning eats budget?
    msg, fr, u = full_call(
        [{"role": "user", "content": "写一段500字的产品介绍"}], max_tokens=30
    )
    print("trunc: finish_reason:", fr, "completion_tokens:", getattr(u, "completion_tokens", None), "content:", repr((msg.content or "")[:80]))

    # 4) system role with enough budget
    r1 = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "推荐一个周末活动"}],
        max_tokens=400,
    )
    r2 = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": '你只输出 JSON，格式为 {"activity": "..."}，不要输出其他内容'},
            {"role": "user", "content": "推荐一个周末活动"},
        ],
        max_tokens=400,
    )
    print("no-system:", repr(r1.choices[0].message.content.strip()[:80]))
    print("system   :", repr(r2.choices[0].message.content.strip()[:80]))


if __name__ == "__main__":
    main()
