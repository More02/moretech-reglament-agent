"""Учёт расходов на модель: журнал вызовов и дневной расход для лимита."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from reglament_agent.adapters.db import LlmCallRow
from skill_sdk import SkillContext, Usage


class UsageLedger:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def record(self, usage: Usage) -> None:
        with self.sessions.begin() as s:
            s.add(
                LlmCallRow(
                    prompt=usage.prompt,
                    model=usage.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost_rub=usage.cost_rub,
                    latency_ms=usage.latency_ms,
                )
            )

    def record_context(self, ctx: SkillContext) -> None:
        """Тестовая модель не пишет расход сама (у настоящего шлюза есть on_usage) - сохраняем из контекста."""
        for call in ctx.usage.calls:
            if call.model == "fake":
                self.record(call)

    def spent_today(self) -> float:
        since = datetime.now(UTC) - timedelta(days=1)
        with self.sessions() as s:
            total = s.scalar(
                select(func.coalesce(func.sum(LlmCallRow.cost_rub), 0.0)).where(LlmCallRow.created_at >= since)
            )
            return float(total or 0.0)
