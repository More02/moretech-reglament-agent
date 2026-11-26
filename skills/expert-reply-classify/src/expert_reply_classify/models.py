"""Вход и выход разбора письма эксперта."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SenderRole(StrEnum):
    QUALITY = "quality"
    ADDED_BY_QUALITY = "added_by_quality"
    EMPLOYEE = "employee"
    UNKNOWN = "unknown"


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender: str
    body: str


class ClassifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    thread: list[Message] = Field(default_factory=list)
    message: Message
    sender_role: SenderRole


class ReplyKind(StrEnum):
    FINAL_ANSWER = "final_answer"
    QUESTION_TO_EMPLOYEE = "question_to_employee"
    FORWARDED_TO_OWNER = "forwarded_to_owner"
    ACKNOWLEDGEMENT = "acknowledgement"
    OTHER = "other"


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ReplyKind
    answer_text: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)
    decided_by: str = Field(default="model", description="model | marker | role")
