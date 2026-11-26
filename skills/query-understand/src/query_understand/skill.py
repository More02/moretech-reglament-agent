"""Скилл понимания вопроса: модель разбирает, код проверяет идентификаторы и чинит пустые поля."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from query_understand.models import Intent, Understanding, UnderstandInput
from skill_sdk import Issue, Level, Skill, SkillContext

SKILL_DIR = Path(__file__).resolve().parents[2]


class QueryUnderstand(Skill[UnderstandInput, Understanding]):
    skill_dir: ClassVar[Path] = SKILL_DIR

    def run(self, inp: UnderstandInput, ctx: SkillContext) -> Understanding:
        ctx.progress("Разбираю вопрос")
        raw = self.ask(
            ctx,
            "understand",
            content=inp.model_dump(exclude_defaults=False),
            output=Understanding,
        )
        return self.sanitize(raw, inp)

    @staticmethod
    def sanitize(out: Understanding, inp: UnderstandInput) -> Understanding:
        """Выдуманные подразделения и темы отбрасываются; пустые запросы заменяются вопросом."""
        known = {d.id for d in inp.departments}
        departments = list(dict.fromkeys(d for d in out.departments if d in known))
        topic = out.out_of_scope_topic
        if topic is not None and not 0 <= topic < len(inp.out_of_scope_topics):
            topic = None
        intent = out.intent
        if intent is Intent.OUT_OF_SCOPE and topic is None and inp.out_of_scope_topics:
            topic = 0
        standalone = out.standalone_question.strip() or inp.question.strip()
        queries = [q.strip() for q in out.search_queries if q.strip()] or [standalone]
        return out.model_copy(
            update={
                "departments": departments,
                "out_of_scope_topic": topic,
                "standalone_question": standalone,
                "search_queries": queries[:3],
                "complex_project": out.complex_project or len(departments) > 1,
            }
        )

    def checks(self, out: Understanding, inp: UnderstandInput) -> list[Issue]:
        issues: list[Issue] = []
        if out.intent is Intent.REGULATION_QUESTION and not out.search_queries:
            issues.append(Issue(Level.ERROR, "no_queries", "нет поисковых запросов"))
        unknown = set(out.departments) - {d.id for d in inp.departments}
        if unknown:
            issues.append(Issue(Level.ERROR, "unknown_department", f"неизвестные подразделения: {sorted(unknown)}"))
        return issues
