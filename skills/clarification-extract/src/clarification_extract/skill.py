"""Извлечение разъяснения: модель обобщает, код проверяет опору на письмо и идентификаторы."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from clarification_extract.models import Clarification, ExtractInput
from evidence import find_quote
from skill_sdk import Issue, Level, Skill, SkillContext

SKILL_DIR = Path(__file__).resolve().parents[2]


class ClarificationExtract(Skill[ExtractInput, Clarification]):
    skill_dir: ClassVar[Path] = SKILL_DIR

    def run(self, inp: ExtractInput, ctx: SkillContext) -> Clarification:
        ctx.progress("Оформляю разъяснение службы качества")
        raw = self.ask(ctx, "extract", content=inp.model_dump(), output=Clarification)
        return self.sanitize(raw, inp)

    @staticmethod
    def sanitize(out: Clarification, inp: ExtractInput) -> Clarification:
        quotes = [q for q in out.answer_quotes if find_quote(q, inp.expert_answer) is not None]
        answer = out.answer.strip()
        # Ответ без дословной опоры на письмо не публикуем пересказом: берём текст эксперта.
        if not quotes or not answer:
            answer = inp.expert_answer.strip()
        clause_ids = {c.id for c in inp.candidate_clauses}
        return out.model_copy(
            update={
                "answer": answer,
                "answer_quotes": quotes,
                "department_ids": [d for d in dict.fromkeys(out.department_ids) if d in inp.departments],
                "related_clause_ids": [c for c in dict.fromkeys(out.related_clause_ids) if c in clause_ids],
                "canonical_question": out.canonical_question.strip() or inp.question.strip(),
                "keywords": [k.strip() for k in out.keywords if k.strip()][:8],
            }
        )

    def checks(self, out: Clarification, inp: ExtractInput) -> list[Issue]:
        if not out.answer_quotes:
            return [Issue(Level.WARNING, "no_quotes", "ответ взят из письма целиком: модель не дала дословных опор")]
        return []
