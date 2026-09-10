"""Ch33 live 冒烟（mock server 场景，无需真实 Ollama）：

  1. 同步直答   —— quick 请求走分流 sync 路径
  2. 长任务 Job —— 全生命周期 accepted→queued→started→(progress)→done
  3. 降级一     —— mock server 置 down → 回退链第二层接管（degraded=True）
  4. 降级二     —— 回退链也挂 → 同步请求降级为"排队/稍后通知"（Ch35 矩阵）

运行：PYTHONPATH=src:../ch11-model-gateway/src .venv/bin/python examples/smoke_live.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mock_ollama_server import MockOllamaServer  # noqa: E402

from model_gateway.base import FakeProvider, OllamaProvider  # noqa: E402
from model_gateway.gateway import Gateway, GatewayConfig  # noqa: E402
from model_gateway.retry import RetryPolicy  # noqa: E402
from model_gateway.router import Router, Tier  # noqa: E402

from ai_backend.api import ApiLayer, TaskRequest  # noqa: E402


def main():
    server = MockOllamaServer(mode="ok")
    server.start()
    primary = OllamaProvider(base_url=server.base_url, model="qwen3.5:9b-mlx")
    fallback = FakeProvider(["[fake-9b] 回退层回答：主模型不可用，已用备用层生成（降级可见）。"])

    gateway = Gateway(GatewayConfig(
        router=Router([
            Tier("local-9b", primary, "standard", 0.0, "local"),
            Tier("fallback", fallback, "economy", 0.0, "local"),
        ]),
        retry=RetryPolicy(max_attempts=2, base_delay=0.05, cap=0.2),
    ))
    api = ApiLayer(gateway)
    api.start_workers(2)

    print("== 1. 同步直答（quick → sync 路径）==")
    r = api.handle("user-a", TaskRequest(goal="给这篇文章起个标题"))
    print(f"   route={r.route} status={r.status} degraded={r.degraded}\n   answer={r.answer}")

    print("\n== 2. 长任务 Job 全生命周期（long → 入队 → Worker 执行）==")
    r = api.handle("user-a", TaskRequest(goal="8 分钟的深度分析", kind="long", steps=3))
    job_id = r.job_id
    print(f"   提交即断连：job_id={job_id} status={r.status}")
    assert api.wait_idle(timeout=15.0)
    job = api.get_job(job_id)
    print(f"   终态：{job.status} progress={job.progress} result={job.result}")
    print(f"   事件流：{api.events.stages_of(job_id)}")

    print("\n== 3. 降级一：主模型 down → 回退链接管（degraded 可见）==")
    server.set_mode("down")
    r = api.handle("user-b", TaskRequest(goal="再起一个标题"))
    print(f"   status={r.status} degraded={r.degraded}\n   answer={r.answer}")

    print("\n== 4. 降级二：回退链也挂 → 排队/稍后通知（Ch35 矩阵）==")
    fallback.fail_first = 10**9  # 第二层也宕机
    r = api.handle("user-c", TaskRequest(goal="明示降级的请求"))
    print(f"   status={r.status} degraded={r.degraded} job_id={r.job_id}")
    assert api.wait_idle(timeout=15.0)
    job = api.get_job(r.job_id)
    print(f"   后台 Job 诚实终局：{job.status} error={job.error}")
    print(f"   degraded 事件：{[e.payload for e in api.replay() if e.stage == 'degraded'][:1]}")

    api.stop_workers()
    server.set_mode("ok")
    server.stop()
    print("\nsmoke OK")


if __name__ == "__main__":
    main()
