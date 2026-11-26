"""Проверяющий скилл: вердикт модели по каждому утверждению; код следит за полнотой и идентификаторами."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from answer_verify.models import ClaimVerdict, Verdict, VerifyInput, VerifyOutput
from skill_sdk import Issue, Level, Skill, SkillContext

SKILL_DIR = Path(__file__).resolve().parents[2]


class AnswerVerify(Skill[VerifyInput, VerifyOutput]):
    skill_dir: ClassVar[Path] = SKILL_DIR

    def run(self, inp: VerifyInput, ctx: SkillContext) -> VerifyOutput:
        if not inp.claims:
            return VerifyOutput()
        ctx.progress("Перепроверяю ответ")
        raw = self.ask(ctx, "verify", content=inp.model_dump(), output=VerifyOutput)
        known = {c.id for c in inp.claims}
        by_id = {v.id: v for v in raw.verdicts if v.id in known}
        # Утверждение без вердикта считаем непроверенным: в строгом режиме оно не попадёт в ответ.
        verdicts = [
            by_id.get(c.id) or ClaimVerdict(id=c.id, verdict=Verdict.UNSUPPORTED, comment="нет вердикта проверяющего")
            for c in inp.claims
        ]
        return VerifyOutput(verdicts=verdicts)

    def checks(self, out: VerifyOutput, inp: VerifyInput) -> list[Issue]:
        del inp
        return [
            Issue(Level.WARNING, v.verdict.value, f"{v.id}: {v.comment}")
            for v in out.verdicts
            if v.verdict != "supported"
        ]
