"""Объекты, которыми агент обменивается с интерфейсом и каналами (веб, DION, почта)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Profile(BaseModel):
    """Профиль сотрудника (имитация корпоративного входа)."""

    model_config = ConfigDict(extra="forbid")
    name: str
    email: str
    position: str = ""
    department: str | None = None


class ReplyKind(StrEnum):
    ANSWER = "answer"
    CLARIFY = "clarify"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    ESCALATION_SENT = "escalation_sent"
    OUT_OF_SCOPE = "out_of_scope"
    OFF_TASK = "off_task"
    GREETING = "greeting"
    DOCUMENT = "document"
    ERROR = "error"


class Option(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str


class ClaimView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    source_id: str
    source_title: str
    quote: str
    from_quality: bool = False


class VariantView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department_id: str
    department_name: str
    status: str
    lead: str = ""
    claims: list[ClaimView] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    gap: str | None = None


class DocumentView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    department_name: str
    url: str


class UsageView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_tokens: int = 0
    output_tokens: int = 0
    cost_rub: float = 0.0
    latency_ms: int = 0
    llm_calls: int = 0


class TicketView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    status: str
    quality_email: str


class AgentReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ReplyKind
    text: str
    variants: list[VariantView] = Field(default_factory=list)
    options: list[Option] = Field(default_factory=list)
    documents: list[DocumentView] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    ticket: TicketView | None = None
    usage: UsageView = Field(default_factory=UsageView)
    # Сколько утверждений модели проверил код и сколько отбросил (нет цитаты, чужой пункт, число не из цитаты).
    checked_claims: int = 0
    rejected_claims: int = 0
    turn_id: int | None = None
