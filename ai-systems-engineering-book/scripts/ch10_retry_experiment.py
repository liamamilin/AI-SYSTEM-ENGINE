"""Ch10 experiment: retry policy comparison against a flaky endpoint.

Runs a local mock server that returns 429 for the first K calls it receives in
each "wave" (simulating a rate-limited provider), then compares:

  A. no-retry            -> high failure rate
  B. fixed-interval retry, no jitter, all clients aligned -> amplification
  C. exponential backoff + jitter -> converges

Metrics: client success rate, total requests sent to server (amplification).
Pure local simulation — no LLM involved.
"""

import asyncio
import httpx
import random
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 18099
SERVER_STATE = {"received": 0, "served_ok": 0, "rejected": 0}
LOCK = threading.Lock()
LIMIT_PER_WINDOW = 12  # server allows 12 ok responses per 1s window


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        with LOCK:
            SERVER_STATE["received"] += 1
            window = int(time.time())
            ok_in_window = SERVER_STATE.get(f"ok_{window}", 0)
            if ok_in_window >= LIMIT_PER_WINDOW:
                SERVER_STATE["rejected"] += 1
                self.send_response(429)
                self.end_headers()
                return
            SERVER_STATE[f"ok_{window}"] = ok_in_window + 1
            SERVER_STATE["served_ok"] += 1
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):  # silence
        pass


async def call_once(client: httpx.AsyncClient) -> bool:
    try:
        r = await client.post(f"http://127.0.0.1:{PORT}/call", content=b"{}")
        return r.status_code == 200
    except Exception:
        return False


async def strategy_none(client):
    return await call_once(client)


async def strategy_fixed(client):
    for _ in range(4):
        if await call_once(client):
            return True
        await asyncio.sleep(0.5)  # fixed interval, no jitter -> waves align
    return False


async def strategy_backoff(client):
    for attempt in range(4):
        if await call_once(client):
            return True
        await asyncio.sleep(min(0.2 * (2 ** attempt), 3) * random.uniform(0.5, 1.5))
    return False


async def run_batch(name: str, strategy, n_clients: int = 30):
    for k in list(SERVER_STATE):
        if k.startswith("ok_"):
            del SERVER_STATE[k]
    SERVER_STATE.update({"received": 0, "served_ok": 0, "rejected": 0})
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*(strategy(client) for _ in range(n_clients)))
    ok = sum(results)
    print(
        f"{name:28s} success={ok}/{n_clients}  server_received={SERVER_STATE['received']}"
        f"  (amplification x{SERVER_STATE['received'] / n_clients:.1f},"
        f" 429s={SERVER_STATE['rejected']})"
    )
    return ok


async def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    await asyncio.sleep(0.2)

    print(f"mock server: 429 beyond {LIMIT_PER_WINDOW} ok/window(1s)\n")
    await run_batch("A. no-retry", strategy_none)
    await asyncio.sleep(1.2)
    await run_batch("B. fixed-interval retry(4)", strategy_fixed)
    await asyncio.sleep(1.2)
    await run_batch("C. backoff+jitter retry(4)", strategy_backoff)
    server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
