"""LLM + embedding clients (local Ollama by default; same abstraction as Ch8).

注意：Ollama 的 OpenAI-compat 端点忽略 think 参数（2026-09-10 实测，与 Ch7 一致），
因此 ollama provider 走原生 /api/chat 显式传 think=False；云端供应商走 OpenAI-compat。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass
class Completion:
    text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int


class LLMClient(Protocol):
    def complete(
        self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion: ...


class OllamaClient:
    """原生 /api/chat + think=False（本地默认）。"""

    def __init__(self, base_url: str | None = None, model: str | None = None, think: bool = False):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE", "http://localhost:11434")
        self.model = model or os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")
        self.think = think
        self._http = httpx.Client(timeout=600.0)

    def complete(
        self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": self.think,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        r = self._http.post(f"{self.base_url}/api/chat", json=body)
        r.raise_for_status()
        data = r.json()
        return Completion(
            text=data.get("message", {}).get("content") or "",
            finish_reason=data.get("done_reason", "unknown"),
            prompt_tokens=data.get("prompt_eval_count", 0) or 0,
            completion_tokens=data.get("eval_count", 0) or 0,
        )


class OpenAICompatClient:
    """任意 OpenAI-compatible 端点（云端供应商只改环境变量，代码零改动）。"""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "ollama")
        self.model = model or os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")
        self._http = httpx.Client(timeout=600.0)

    def complete(
        self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        r = self._http.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        r.raise_for_status()
        data = r.json()
        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return Completion(
            text=choice["message"].get("content") or "",
            finish_reason=choice.get("finish_reason") or "unknown",
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
        )


def make_client(provider: str | None = None) -> LLMClient:
    provider = provider or os.environ.get("LLM_PROVIDER", "ollama")
    return OpenAICompatClient() if provider == "openai" else OllamaClient()


class OllamaEmbedder:
    """bge-m3 via Ollama /api/embed（embedding 只在索引时批量 + 查询时单条）。"""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE", "http://localhost:11434")
        self.model = model or os.environ.get("EMBED_MODEL", "bge-m3")
        self._http = httpx.Client(timeout=300.0)

    def embed(self, texts: list[str]) -> list[list[float]]:
        r = self._http.post(f"{self.base_url}/api/embed", json={"model": self.model, "input": texts})
        r.raise_for_status()
        return r.json()["embeddings"]
