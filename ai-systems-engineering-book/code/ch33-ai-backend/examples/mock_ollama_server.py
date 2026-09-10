"""Mock Ollama server: ThreadingHTTPServer 模拟 Ollama 原生 /api/chat（Ch10 mock 写法）.

控制端点：POST /control {"mode": "ok" | "down"} —— "down" 时 /api/chat 返回 500，
用于演示降级矩阵的"模型 API 故障 → 回退链"路径。无真实 LLM 依赖。
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockOllamaHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        if self.path == "/control":
            mode = json.loads(body).get("mode", "ok")
            self.server.mode = mode  # type: ignore[attr-defined]
            self._reply(200, {"mode": mode})
            return
        if self.path == "/api/chat":
            if self.server.mode == "down":  # type: ignore[attr-defined]
                self._reply(500, {"error": "mock model down"})
                return
            req = json.loads(body)
            model = req.get("model", "mock-9b")
            prompt = req.get("messages", [{}])[-1].get("content", "")
            self._reply(200, {
                "model": model,
                "message": {"role": "assistant", "content": f"[{model}] 已处理：{prompt[:40]}"},
                "done": True,
                "prompt_eval_count": 10,
                "eval_count": 20,
            })
            return
        self._reply(404, {"error": "not found"})

    def _reply(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence
        pass


class MockOllamaServer:
    def __init__(self, mode: str = "ok"):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockOllamaHandler)
        self.httpd.mode = mode  # type: ignore[attr-defined]
        self.thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    def start(self):
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def set_mode(self, mode: str):
        self.httpd.mode = mode  # type: ignore[attr-defined]

    def stop(self):
        self.httpd.shutdown()
