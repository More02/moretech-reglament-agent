"""Скилл ответа: модель формулирует варианты по подразделениям, код проверяет каждое утверждение."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from answer_compose.models import ComposeInput, Composition, VerifiedComposition
from answer_compose.verify import verify_composition
from skill_sdk import Issue, Level, Skill, SkillContext

SKILL_DIR = Path(__file__).resolve().parents[2]


class AnswerCompose(Skill[ComposeInput, VerifiedComposition]):
    skill_dir: ClassVar[Path] = SKILL_DIR

    def run(self, inp: ComposeInput, ctx: SkillContext) -> VerifiedComposition:
        if not any(d.sources for d in inp.departments) and not inp.expert_notes:
            return verify_composition(Composition(variants=[]), inp)
        ctx.progress("Сверяю ответ с текстом регламентов")
        raw = self.ask(ctx, "compose", content=inp.model_dump(), output=Composition)
        return verify_composition(raw, inp)

    def checks(self, out: VerifiedComposition, inp: ComposeInput) -> list[Issue]:
        return [
            Issue(Level.WARNING, "claim_rejected", f"{r.department_id}: {r.reason}: «{r.claim.text}»")
            for r in out.rejected
        ]
