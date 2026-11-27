"""Клиент модели: интерфейс, учёт токенов и стоимости, тестовая модель."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Usage:
    """Расход одного вызова модели."""

    model: str
    prompt: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_rub: float = 0.0
    provider_cost_rub: float = 0.0  # фактическая цена у провайдера API, если он её сообщает


@dataclass
class UsageMeter:
    """Расход за запрос пользователя: сумма по всем вызовам модели."""

    calls: list[Usage] = field(default_factory=list)

    def add(self, usage: Usage) -> None:
        self.calls.append(usage)

    @property
    def input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def cost_rub(self) -> float:
        return round(sum(c.cost_rub for c in self.calls), 4)

    @property
    def latency_ms(self) -> int:
        return sum(c.latency_ms for c in self.calls)


class LLMError(RuntimeError):
    """Модель недоступна или вернула не JSON."""


class LLMClient(Protocol):
    """Модель, которая отвечает JSON-объектом."""

    def complete_json(
        self, *, prompt_name: str, system: str, user: str, schema: Mapping[str, Any]
    ) -> tuple[str, Usage]:
        """Возвращает сырой JSON-текст ответа и расход."""
        ...


Handler = Callable[[str], Mapping[str, Any]]


class FakeLLM:
    """Тестовая модель: обработчик по имени промпта получает пользовательскую часть и возвращает ответ."""

    def __init__(self, handlers: Mapping[str, Handler]) -> None:
        self.handlers = dict(handlers)
        self.requests: list[tuple[str, str]] = []

    def complete_json(
        self, *, prompt_name: str, system: str, user: str, schema: Mapping[str, Any]
    ) -> tuple[str, Usage]:
        del system, schema
        self.requests.append((prompt_name, user))
        if prompt_name not in self.handlers:
            raise LLMError(f"тестовая модель не знает промпт {prompt_name}")
        payload = json.dumps(self.handlers[prompt_name](user), ensure_ascii=False)
        usage = Usage(
            model="fake",
            prompt=prompt_name,
            input_tokens=len(user) // 3,
            output_tokens=len(payload) // 3,
            latency_ms=0,
        )
        return payload, usage
