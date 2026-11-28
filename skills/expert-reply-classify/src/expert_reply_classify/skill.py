"""Разбор письма эксперта: права и метки решает код, смысл письма - модель."""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

from evidence import find_quote
from expert_reply_classify.models import Classification, ClassifyInput, ReplyKind, SenderRole
from skill_sdk import Issue, Level, Skill, SkillContext

SKILL_DIR = Path(__file__).resolve().parents[2]
ANSWER_MARKER = re.compile(r"#ответ\b", re.IGNORECASE)
DRAFT_MARKER = re.compile(r"#черновик\b", re.IGNORECASE)
_AUTHORIZED = (SenderRole.QUALITY, SenderRole.ADDED_BY_QUALITY)
# Начало процитированного письма: метки из цитаты (в письме агента есть подсказка про «#черновик») не учитываем.
QUOTE_START = re.compile(
    r"^\s*(?:-{4,}|_{4,}|>|(?:От|From|Кому|To|Тема|Subject)\s*:|.*\bпишет:\s*$|.*\bwrote:\s*$)",
    re.IGNORECASE | re.MULTILINE,
)


def own_text(body: str) -> str:
    """Текст, написанный автором письма, без процитированной переписки."""
    m = QUOTE_START.search(body)
    return body[: m.start()].strip() if m else body.strip()


class ExpertReplyClassify(Skill[ClassifyInput, Classification]):
    skill_dir: ClassVar[Path] = SKILL_DIR

    def run(self, inp: ClassifyInput, ctx: SkillContext) -> Classification:
        body = own_text(inp.message.body)
        if inp.sender_role not in _AUTHORIZED:
            # Сотрудник или посторонний не может дать нормативный ответ - это уточнение в переписке.
            return Classification(kind=ReplyKind.OTHER, confidence=1.0, decided_by="role")
        if DRAFT_MARKER.search(body):
            return Classification(kind=ReplyKind.OTHER, confidence=1.0, decided_by="marker")
        content = inp.model_dump()
        content["message"]["body"] = body
        raw = self.ask(ctx, "classify", content=content, output=Classification)
        if ANSWER_MARKER.search(body):
            text = raw.answer_text or ANSWER_MARKER.sub("", body).strip()
            raw = Classification(kind=ReplyKind.FINAL_ANSWER, answer_text=text, confidence=1.0, decided_by="marker")
        return self._faithful(raw, body)

    @staticmethod
    def _faithful(out: Classification, body: str) -> Classification:
        """Ответ должен быть взят из письма: если модель пересказала слишком вольно - берём текст письма целиком."""
        if out.kind is not ReplyKind.FINAL_ANSWER:
            return out.model_copy(update={"answer_text": ""})
        text = out.answer_text.strip()
        if not text or find_quote(text, body, threshold=85.0) is None:
            return out.model_copy(update={"answer_text": ANSWER_MARKER.sub("", body).strip()})
        return out

    def checks(self, out: Classification, inp: ClassifyInput) -> list[Issue]:
        if out.kind is ReplyKind.FINAL_ANSWER and inp.sender_role not in _AUTHORIZED:
            return [Issue(Level.ERROR, "unauthorized_answer", "финальный ответ от неуполномоченного отправителя")]
        return []
