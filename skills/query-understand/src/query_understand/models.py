"""Вход и выход скилла понимания вопроса."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Intent(StrEnum):
    REGULATION_QUESTION = "regulation_question"
    FIND_DOCUMENT = "find_document"
    OUT_OF_SCOPE = "out_of_scope"
    OFF_TASK = "off_task"
    GREETING = "greeting"


class Process(StrEnum):
    PRESALE = "presale"
    PROJECT = "project"


class DepartmentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(description="employee или agent")
    text: str


class UnderstandInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    history: list[Turn] = Field(default_factory=list)
    departments: list[DepartmentRef]
    glossary_hits: dict[str, str] = Field(default_factory=dict, description="сокращение/синоним → термин")
    out_of_scope_topics: list[str] = Field(default_factory=list)


class Understanding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Intent
    standalone_question: str
    search_queries: list[str] = Field(default_factory=list, max_length=3)
    departments: list[str] = Field(default_factory=list)
    complex_project: bool = False
    process: Process | None = None
    out_of_scope_topic: int | None = None
