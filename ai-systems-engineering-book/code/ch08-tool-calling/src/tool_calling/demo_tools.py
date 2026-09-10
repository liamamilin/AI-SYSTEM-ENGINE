"""Ch8 demo tools: deterministic, no side effects, runnable locally.

- calculator: real arithmetic (the whole point: the model must NOT do math itself)
- get_weather: canned data (deterministic; a stand-in for any read-only API)
"""

from tool_calling.registry import ToolRegistry

registry = ToolRegistry()


@registry.register(
    name="calculator",
    description="计算一个四则运算表达式。仅支持 + - * / ( ) 和数字。",
)
def calculator(expression: str) -> float:
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        raise ValueError(f"illegal characters in expression: {expression!r}")
    result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307 - sandboxed + charset-checked
    return float(result)


_WEATHER = {
    "北京": {"temp_c": 22, "condition": "晴"},
    "上海": {"temp_c": 26, "condition": "多云"},
    "深圳": {"temp_c": 30, "condition": "阵雨"},
}


@registry.register(
    name="get_weather",
    description="查询城市当前天气。支持的城市：北京、上海、深圳。",
    schema={"city": {"type": "string", "required": True}},
)
def get_weather(city: str) -> dict:
    city = city.strip()
    for name, data in _WEATHER.items():
        if name in city:
            return data
    raise ValueError(f"unsupported city: {city!r} (supported: {list(_WEATHER)})")
