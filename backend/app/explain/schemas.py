from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

DISCLAIMER = {
    "en": "ClearKo explains documents to help you understand them. It is not legal advice. "
    "Check important points with the other party, a lawyer or an official counter.",
    "ru": "ClearKo объясняет документы, чтобы помочь вам их понять. Это не юридическая "
    "консультация. Важные моменты проверяйте у другой стороны, юриста или в официальной службе.",
    "uz": "ClearKo hujjatlarni tushunishingizga yordam beradi. Bu yuridik maslahat emas. "
    "Muhim jihatlarni boshqa tomon, advokat yoki rasmiy idora bilan tekshiring.",
}


class DocType(str, Enum):
    RENTAL = "rental"
    PHONE_PLAN = "phone_plan"
    PART_TIME = "part_time"
    UNSUPPORTED = "unsupported"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class KeyFact(BaseModel):
    label: str
    value: str
    original_text: str | None = None  # verbatim from the scan, when the fact comes from a clause
    quote_verified: bool = False


class RedFlag(BaseModel):
    title: str
    explanation: str
    original_text: str | None = None
    quote_verified: bool = False
    severity: Severity = Severity.MEDIUM


class Todo(BaseModel):
    action: str
    deadline: str | None = None


class LLMOutput(BaseModel):
    """What the model is asked to return (no doc_type/disclaimer: we set those ourselves)."""

    summary: str
    key_facts: list[KeyFact] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    todos: list[Todo] = Field(default_factory=list)


class Explanation(LLMOutput):
    doc_type: DocType
    language: str
    disclaimer: str
    ocr_confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
