"""Манифест скилла (skill.yaml)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class DataClass(StrEnum):
    """Какие данные видит скилл - определяет, нужен ли шлюз обезличивания."""

    PUBLIC = "public"
    COMPANY = "company"
    PERSONAL = "personal"


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    entry: str
    name: str
    version: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    data_class: DataClass
    models: list[str] = Field(default_factory=list)
    timeout_seconds: int = 30
    verify: dict[str, str] = Field(default_factory=lambda: {"mode": "code"})
    cost_estimate: dict[str, int] = Field(default_factory=dict)
    stability: str = "experimental"

    @classmethod
    def load(cls, skill_dir: Path) -> Manifest:
        with (skill_dir / "skill.yaml").open(encoding="utf-8") as fh:
            return cls.model_validate(yaml.safe_load(fh))
