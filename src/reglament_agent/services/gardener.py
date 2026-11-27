"""Агент-садовник: следит, чтобы база знаний не устаревала и служба качества видела пробелы в регламентах."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from gap_cluster import Cluster, ClusterInput, GapCluster, GapQuestion
from reglament_agent.adapters.db import NoteRow, TurnRow
from reglament_agent.adapters.mail import MailTransport, OutgoingMail
from reglament_agent.passport import Passport
from reglament_agent.services.knowledge import KnowledgeBase
from skill_sdk import LLMClient, LLMError, SkillContext

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GardenReport:
    clusters: list[Cluster]
    notes_need_review: int
    digest_sent: bool


class Gardener:
    def __init__(
        self,
        *,
        sessions: sessionmaker[Session],
        passport: Passport,
        kb: KnowledgeBase,
        llm: LLMClient,
        mail: MailTransport,
        quality_email: str,
        on_usage: Callable[[SkillContext], None] = lambda _c: None,
    ) -> None:
        self.sessions = sessions
        self.passport = passport
        self.kb = kb
        self.llm = llm
        self.mail = mail
        self.quality_email = quality_email
        self.on_usage = on_usage
        self.skill = GapCluster()

    def gaps(self, days: int = 30) -> list[Cluster]:
        since = datetime.now(UTC) - timedelta(days=days)
        with self.sessions() as s:
            turns = s.scalars(select(TurnRow).where(TurnRow.created_at >= since).order_by(TurnRow.id)).all()
        questions: list[GapQuestion] = []
        last: dict[str, TurnRow] = {}
        for t in turns:
            if t.role == "employee":
                last[t.conversation_id] = t
            elif t.outcome in ("not_found", "conflict", "escalation_sent") and t.conversation_id in last:
                q = last[t.conversation_id]
                questions.append(GapQuestion(id=str(q.id), text=q.text))
        if not questions:
            return []
        ctx = SkillContext(llm=self.llm)
        try:
            return self.skill.run(
                ClusterInput(questions=questions[-100:], documents=[d.title for d in self.passport.documents]), ctx
            ).clusters
        finally:
            self.on_usage(ctx)

    def run(self, *, send_digest: bool = False) -> GardenReport:
        try:
            clusters = self.gaps()
        except LLMError:
            log.exception("не удалось сгруппировать вопросы")
            clusters = []
        with self.sessions() as s:
            review = s.scalars(select(NoteRow).where(NoteRow.status == "needs_review")).all()
        sent = False
        if send_digest and (clusters or review):
            lines = ["Сводка агента по регламентам для службы качества.", ""]
            if review:
                lines.append("Разъяснения, которые нужно перепроверить из-за изменения регламентов:")
                lines += [f"- №{n.id}: {n.canonical_question} ({n.review_reason})" for n in review]
                lines.append("")
            if clusters:
                lines.append("Темы вопросов, на которые в регламентах нет ответа:")
                lines += [f"- {c.title} ({len(c.question_ids)} вопр.): {c.suggestion}" for c in clusters]
            self.mail.send(
                OutgoingMail(
                    to=[self.quality_email], cc=[], subject="Сводка: пробелы в регламентах", body="\n".join(lines)
                )
            )
            sent = True
        return GardenReport(clusters=clusters, notes_need_review=len(review), digest_sent=sent)
