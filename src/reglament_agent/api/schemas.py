"""Схемы запросов API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from reglament_agent.domain import Profile


class StartConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: Profile


class AskMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)


class ChooseOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: str = Field(min_length=1, max_length=100)


class Rating(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: int = Field(ge=-1, le=1)


class NoteStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(published|retired|needs_review|disputed)$")
    reason: str = ""


class WebhookMessage(BaseModel):
    """Входящее сообщение канала (DION и другие мессенджеры с исходящими вебхуками)."""

    model_config = ConfigDict(extra="forbid")
    chat_id: str = Field(min_length=1, max_length=200)
    user: Profile
    text: str = Field(default="", max_length=2000)
    option_id: str | None = None
