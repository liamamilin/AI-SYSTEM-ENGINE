"""Tool registry: tools as first-class objects with schema auto-generation.

Ch8 core boundary: the model PROPOSES (name + arguments JSON); the host
validates and EXECUTES. The registry is the host-side source of truth.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError, create_model


@dataclass
class ToolResult:
    ok: bool
    value: Any = None
    error: str | None = None


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    schema: dict  # JSON-schema-ish: {param: {"type": ..., "description": ...}}

    def validate_args(self, args: dict) -> tuple[dict | None, str | None]:
        """Coerce + validate arguments against the declared schema."""
        cleaned: dict[str, Any] = {}
        for pname, spec in self.schema.items():
            if pname not in args:
                if spec.get("required", True):
                    return None, f"missing required argument: {pname}"
                continue
            v = args[pname]
            t = spec.get("type", "string")
            try:
                if t == "number":
                    v = float(v) if not isinstance(v, (int, float)) else v
                elif t == "integer":
                    v = int(v)
                elif t == "boolean":
                    if isinstance(v, str):
                        v = v.lower() in ("true", "1", "yes")
                elif t == "string":
                    v = str(v)
                # array/object: pass through, handler validates
            except (TypeError, ValueError):
                return None, f"argument {pname!r} must be of type {t}, got {v!r}"
            cleaned[pname] = v
        extra = set(args) - set(self.schema)
        if extra:
            return None, f"unknown arguments: {sorted(extra)}"
        return cleaned, None


def schema_from_signature(func: Callable) -> dict:
    """Best-effort schema from type hints; explicit schema overrides this."""
    out: dict[str, dict] = {}
    sig = inspect.signature(func)
    for pname, param in sig.parameters.items():
        ann = param.annotation
        if ann is float or ann is int:
            t = "number" if ann is float else "integer"
        elif ann is bool:
            t = "boolean"
        else:
            t = "string"
        out[pname] = {"type": t, "required": param.default is inspect.Parameter.empty}
    return out


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, func: Callable | None = None, *, name: str | None = None,
                 description: str = "", schema: dict | None = None):
        """Register a tool. Works as @registry.register or @registry.register(name=...)."""
        if func is None:
            def deco(f: Callable) -> Tool:
                return self.register(f, name=name, description=description, schema=schema)
            return deco
        tool_name = name or func.__name__
        if " " in tool_name or not tool_name:
            raise ValueError(f"invalid tool name: {tool_name!r}")
        tool = Tool(
            name=tool_name,
            description=description or (func.__doc__ or "").strip(),
            handler=func,
            schema=schema or schema_from_signature(func),
        )
        self._tools[tool_name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def specs(self) -> list[dict]:
        """Tool specs to inject into the prompt (Ch6 format section)."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.schema,
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, args: dict) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"unknown tool: {name!r}")
        cleaned, err = tool.validate_args(args)
        if err:
            return ToolResult(ok=False, error=f"invalid arguments: {err}")
        try:
            return ToolResult(ok=True, value=tool.handler(**cleaned))
        except Exception as e:  # tool errors are DATA for the model, not crashes
            return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")


def tool_result_message(name: str, result: ToolResult) -> dict:
    """Serialize a ToolResult as a tool-role message the model can learn from."""
    payload = {"value": result.value} if result.ok else {"error": result.error}
    return {
        "role": "tool",
        "name": name,
        "content": json.dumps({"tool": name, **payload}, ensure_ascii=False),
    }
