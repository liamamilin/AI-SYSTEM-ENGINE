"""Output contracts: Pydantic schemas that define what the LLM must return.

The schema is the single source of truth:
- it validates model output,
- its description drives the prompt's format section (Ch6 template).
"""

from pydantic import BaseModel, Field, field_validator

CATEGORY = ("refund", "logistics", "other")
URGENCY = ("low", "medium", "high")


class TicketClassification(BaseModel):
    """Structured classification of a support ticket."""

    category: str = Field(description=f"one of: {', '.join(CATEGORY)}")
    urgency: str = Field(description=f"one of: {', '.join(URGENCY)}")
    summary: str = Field(description="summary of the ticket, <= 20 Chinese characters")
    needs_human: bool = Field(description="true if the ticket is ambiguous or high-risk")

    @field_validator("category")
    @classmethod
    def category_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in CATEGORY:
            raise ValueError(f"category must be one of {CATEGORY}, got: {v!r}")
        return v

    @field_validator("urgency")
    @classmethod
    def urgency_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in URGENCY:
            raise ValueError(f"urgency must be one of {URGENCY}, got: {v!r}")
        return v

    @field_validator("summary")
    @classmethod
    def summary_short(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("summary must not be empty")
        if len(v) > 40:
            raise ValueError(f"summary too long ({len(v)} chars), keep it <= 20 Chinese characters")
        return v


def schema_hint() -> str:
    """Human-readable schema description for the prompt (format section)."""
    return (
        "输出一个 JSON 对象，字段如下：\n"
        '  "category": "refund" | "logistics" | "other"\n'
        '  "urgency": "low" | "medium" | "high"\n'
        '  "summary": "工单摘要，不超过20个汉字"\n'
        '  "needs_human": true | false\n'
        "只输出这个 JSON 对象，不要输出任何其他内容。"
    )
