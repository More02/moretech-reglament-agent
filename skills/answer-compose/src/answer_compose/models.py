"""Вход и выход скилла ответа."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description="clause_id пункта")
    ref: str = Field(description="Как ссылаться: «п. 2.4, Проектная деятельность ДБРЦТ»")
    path: list[str] = Field(default_factory=list)
    text: str


class DepartmentSources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    sources: list[Source]


class ExpertNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description="note:<номер>")
    question: str
    answer: str
    department_ids: list[str] = Field(default_factory=list)
    date: str = ""


class ComposeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    departments: list[DepartmentSources]
    expert_notes: list[ExpertNote] = Field(default_factory=list)


class Status(StrEnum):
    ANSWERED = "answered"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    source_id: str
    quote: str


class Variant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department_id: str
    status: Status
    lead: str = ""
    claims: list[Claim] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    gap: str | None = None


class Conflict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ids: list[str]
    description: str


class Composition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variants: list[Variant]
    same_across_departments: bool = False
    conflict: Conflict | None = None
    missing_documents: list[str] = Field(default_factory=list)


class RejectedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department_id: str
    claim: Claim
    reason: str


class VerifiedComposition(BaseModel):
    """Ответ после проверки кодом: в ``variants`` остались только подтверждённые утверждения."""

    model_config = ConfigDict(extra="forbid")
    variants: list[Variant]
    same_across_departments: bool
    conflict: Conflict | None
    missing_documents: list[str]
    rejected: list[RejectedClaim] = Field(default_factory=list)

    def answered(self) -> list[Variant]:
        return [v for v in self.variants if v.status is not Status.NOT_FOUND]
