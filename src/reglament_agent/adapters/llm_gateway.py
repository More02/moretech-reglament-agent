"""LLM-шлюз: любой OpenAI-совместимый адрес, обезличивание ПДн, учёт стоимости, дневной лимит, повторы."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pii_guard import PiiGuard
from skill_sdk import LLMError, Usage

log = logging.getLogger(__name__)


class BudgetExceededError(LLMError):
    """Дневной лимит расходов на модель исчерпан (защита публичного стенда)."""


class Pricing:
    """Стоимость вызова по ценам официального провайдера модели."""

    def __init__(self, input_usd_per_m: float, output_usd_per_m: float, usd_rub: float) -> None:
        self.input_rub = input_usd_per_m * usd_rub / 1_000_000
        self.output_rub = output_usd_per_m * usd_rub / 1_000_000

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return round(input_tokens * self.input_rub + output_tokens * self.output_rub, 5)


class OpenAICompatibleLLM:
    """Клиент модели. Персональные данные маскируются до отправки и восстанавливаются в ответе."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        pricing: Pricing,
        pii: PiiGuard,
        timeout: float = 40.0,
        spent_today: Callable[[], float] = lambda: 0.0,
        daily_budget_rub: float = 0.0,
        on_usage: Callable[[Usage], None] = lambda _u: None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.pricing = pricing
        self.pii = pii
        self.spent_today = spent_today
        self.daily_budget_rub = daily_budget_rub
        self.on_usage = on_usage
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def complete_json(
        self, *, prompt_name: str, system: str, user: str, schema: Mapping[str, Any]
    ) -> tuple[str, Usage]:
        if self.daily_budget_rub and self.spent_today() >= self.daily_budget_rub:
            raise BudgetExceededError("дневной лимит расходов на модель исчерпан")
        masked = self.pii.mask(user)
        schema_hint = json.dumps(schema, ensure_ascii=False)
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": f"{system}\n\nJSON-схема ответа:\n{schema_hint}"},
                {"role": "user", "content": masked.text},
            ],
            # Qwen3.x: ответ без рассуждений - быстрее и в десятки раз дешевле для извлечения по источникам.
            # Провайдеры понимают разные параметры, поэтому передаём все три (проверено замером reasoning_tokens = 0).
            "reasoning": {"enabled": False},
            "enable_thinking": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        started = time.perf_counter()
        data = self._post(payload)
        latency = int((time.perf_counter() - started) * 1000)
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"неожиданный ответ провайдера: {str(data)[:300]}") from exc
        usage_raw = data.get("usage") or {}
        in_tok = int(usage_raw.get("prompt_tokens", len(masked.text) // 3))
        out_tok = int(usage_raw.get("completion_tokens", len(content) // 3))
        usage = Usage(
            model=self.model,
            prompt=prompt_name,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency,
            cost_rub=self.pricing.cost(in_tok, out_tok),
            provider_cost_rub=float(usage_raw.get("cost_rub") or 0.0),
        )
        self.on_usage(usage)
        return masked.unmask(content), usage

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
    )
    def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post("/chat/completions", json=payload)
        if resp.status_code in (429, 500, 502, 503, 504):
            resp.raise_for_status()
        if resp.status_code >= 400:
            raise LLMError(f"провайдер модели вернул {resp.status_code}: {resp.text[:300]}")
        result: dict[str, Any] = resp.json()
        return result

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._post_with_retry(payload)
        except LLMError:
            raise
        except httpx.HTTPError as exc:
            raise LLMError(f"модель недоступна: {exc}") from exc
