"""Вход и выход проверяющего скилла."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ClaimToCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str
    source_text: str


class VerifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    claims: list[ClaimToCheck]


class Verdict(StrEnum):
    SUPPORTED = "supported"
    DISTORTED = "distorted"
    UNSUPPORTED = "unsupported"


class ClaimVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    verdict: Verdict
    comment: str = ""


class VerifyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdicts: list[ClaimVerdict] = Field(default_factory=list)

    def failed_ids(self) -> set[str]:
        return {v.id for v in self.verdicts if v.verdict is not Verdict.SUPPORTED}
