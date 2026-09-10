"""Provider abstraction: one interface, many endpoints (Ch11 core)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Completion:
    text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    model: str = ""
    raw: dict[str, Any] | None = None
    degraded: bool = False  # set by fallback logic, never by provider


class LLMClient(Protocol):
    def complete(self, messages, *, temperature: float = 0.0, max_tokens: int = 512) -> Completion: ...


class OllamaProvider:
    """Local Ollama native API (think control works here)."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        import urllib.request

        self._urllib = urllib.request
        self.base_url = base_url or os.environ.get("OLLAMA_BASE", "http://localhost:11434")
        self.model = model or "qwen3.5:9b-mlx"

    def complete(self, messages, *, temperature=0.0, max_tokens=512) -> Completion:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": os.environ.get("LLM_THINK", "false").lower() == "true",
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
            model=self.model,
        )


class OpenAICompatProvider:
    """Any OpenAI-compatible endpoint (cloud or self-hosted vLLM)."""

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
            model=self.model,
        )


class FakeProvider:
    """Deterministic provider for tests / offline dev."""

    def __init__(self, outputs: list[str] | None = None, fail_first: int = 0):
        self.outputs = list(outputs or ["fake answer"])
        self.fail_first = fail_first
        self.calls = 0

    def complete(self, messages, *, temperature=0.0, max_tokens=512) -> Completion:
        self.calls += 1
        if self.calls <= self.fail_first:
            raise TimeoutError(f"fake provider down (call {self.calls})")
        text = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        return Completion(text=text, finish_reason="stop", prompt_tokens=1, completion_tokens=1, model="fake")
