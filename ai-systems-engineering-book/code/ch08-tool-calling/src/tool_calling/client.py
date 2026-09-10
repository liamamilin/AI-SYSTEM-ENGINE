"""LLM client for Ch8 (same abstraction as Ch7; unified in Ch11)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Completion:
    text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    raw: dict[str, Any] | None = None


class LLMClient(Protocol):
    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512) -> Completion: ...


class OllamaNativeClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        import urllib.request

        self._urllib = urllib.request
        self.base_url = base_url or os.environ.get("OLLAMA_BASE", "http://localhost:11434")
        self.model = model or os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")
        self.think = os.environ.get("LLM_THINK", "false").lower() == "true"

    def complete(self, messages, *, temperature=0.0, max_tokens=512) -> Completion:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": self.think,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        req = self._urllib.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with self._urllib.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read())
        return Completion(
            text=data.get("message", {}).get("content") or "",
            finish_reason=data.get("done_reason", "unknown"),
            prompt_tokens=data.get("prompt_eval_count", 0) or 0,
            completion_tokens=data.get("eval_count", 0) or 0,
        )


class OpenAICompatClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        from openai import OpenAI

        self.model = model or os.environ.get("LLM_MODEL", "qwen3.5:9b-mlx")
        self._client = OpenAI(
            base_url=base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=api_key or os.environ.get("LLM_API_KEY", "ollama"),
        )

    def complete(self, messages, *, temperature=0.0, max_tokens=512) -> Completion:
        r = self._client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        c = r.choices[0]
        u = r.usage
        return Completion(
            text=c.message.content or "",
            finish_reason=c.finish_reason or "unknown",
            prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(u, "completion_tokens", 0) or 0,
        )


def make_client(provider: str | None = None) -> LLMClient:
    provider = provider or os.environ.get("LLM_PROVIDER", "ollama")
    if provider == "openai":
        return OpenAICompatClient()
    return OllamaNativeClient()
