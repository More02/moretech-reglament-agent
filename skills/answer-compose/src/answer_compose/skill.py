"""Скилл ответа: модель формулирует варианты по подразделениям, код проверяет каждое утверждение."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from answer_compose.models import ComposeInput, Composition, VerifiedComposition
from answer_compose.verify import complete_conditions, lost_conditions, verify_composition
from skill_sdk import Issue, Level, Skill, SkillContext

SKILL_DIR = Path(__file__).resolve().parents[2]


class AnswerCompose(Skill[ComposeInput, VerifiedComposition]):
    skill_dir: ClassVar[Path] = SKILL_DIR

    def run(self, inp: ComposeInput, ctx: SkillContext) -> VerifiedComposition:
        if not any(d.sources for d in inp.departments) and not inp.expert_notes:
            return verify_composition(Composition(variants=[]), inp)
        ctx.progress("Сверяю ответ с текстом регламентов")
        raw = self.ask(ctx, "compose", content=inp.model_dump(), output=Composition)
        out = verify_composition(raw, inp)
        feedback = lost_conditions(out, inp)
        if feedback:
            # Код нашёл правило без второго условия или исключения - один повтор с замечаниями проверки.
            ctx.progress("Дополняю условия правила")
            content = {**inp.model_dump(), "feedback": feedback}
            out = verify_composition(self.ask(ctx, "compose", content=content, output=Composition), inp)
        return complete_conditions(out, inp)

    def checks(self, out: VerifiedComposition, inp: ComposeInput) -> list[Issue]:
        return [
            Issue(Level.WARNING, "claim_rejected", f"{r.department_id}: {r.reason}: «{r.claim.text}»")
            for r in out.rejected
        ]
