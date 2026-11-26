"""Вход и выход извлечения разъяснения."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CandidateClause(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    ref: str
    text: str


class ExtractInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    expert_answer: str
    departments: dict[str, str] = Field(description="id → название")
    employee_department: str | None = None
    candidate_clauses: list[CandidateClause] = Field(default_factory=list)


class Clarification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_question: str
    answer: str
    answer_quotes: list[str] = Field(default_factory=list)
    department_ids: list[str] = Field(default_factory=list)
    related_clause_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
