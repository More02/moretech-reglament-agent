"""Вход и выход группировки вопросов."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GapQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str
    department: str | None = None


class ClusterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[GapQuestion]
    documents: list[str] = Field(default_factory=list)


class Cluster(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    question_ids: list[str]
    suggestion: str = ""


class Clusters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clusters: list[Cluster] = Field(default_factory=list)
