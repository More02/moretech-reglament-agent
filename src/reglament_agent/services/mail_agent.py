"""Почтовый агент: обращение в службу качества, чтение переписки, финальный ответ → разъяснение в базе знаний."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from clarification_extract import CandidateClause, ClarificationExtract, ExtractInput
from evidence import numbers
from expert_reply_classify import ClassifyInput, ExpertReplyClassify, Message, ReplyKind, SenderRole
from reglament_agent.adapters.db import ClauseRow, DocumentRow, MailRow, NoteRow, TicketRow, TurnRow, utcnow
from reglament_agent.adapters.mail import IncomingMail, MailTransport, OutgoingMail
from reglament_agent.domain import AgentReply, Profile, TicketView
from reglament_agent.domain import ReplyKind as ChatKind
from reglament_agent.passport import Passport
from reglament_agent.services.knowledge import KnowledgeBase, clause_ref
from ru_text import lemmas
from skill_sdk import LLMClient, LLMError, SkillContext

log = logging.getLogger(__name__)
CODE_RE = re.compile(r"\[РЕГ-(\d{4,})\]")


@dataclass(frozen=True, slots=True)
class PollReport:
    received: int
    matched: int
    published_notes: list[int]


def answers_differ(a: str, b: str) -> bool:
    """Ответы расходятся по сути: разные числа или мало общих слов. Перефразирование расхождением не считается."""
    if numbers(a) != numbers(b):
        return True
    la, lb = set(lemmas(a)), set(lemmas(b))
    if not la or not lb:
        return False
    return len(la & lb) / len(la | lb) < 0.45


class MailAgent:
    def __init__(
        self,
        *,
        sessions: sessionmaker[Session],
        transport: MailTransport,
        passport: Passport,
        kb: KnowledgeBase,
        llm: LLMClient,
        quality_email: str,
        authorized: list[str],
        public_base_url: str,
        on_usage: Callable[[SkillContext], None] = lambda _c: None,
    ) -> None:
        self.sessions = sessions
        self.transport = transport
        self.passport = passport
        self.kb = kb
        self.llm = llm
        self.quality_email = quality_email.lower()
        self.authorized = [a.lower() for a in authorized]
        self.public_base_url = public_base_url.rstrip("/")
        self.on_usage = on_usage
        self.classifier = ExpertReplyClassify()
        self.extractor = ClarificationExtract()

    # ---------- обращение ----------

    def escalate(
        self, *, conversation_id: str, profile: Profile, question: str, context: str, candidate_clause_ids: list[str]
    ) -> TicketRow:
        with self.sessions.begin() as s:
            ticket = TicketRow(
                conversation_id=conversation_id,
                employee_name=profile.name,
                employee_email=profile.email,
                department=profile.department,
                question=question,
                context=context,
                candidate_clause_ids=candidate_clause_ids,
                status="draft",
            )
            s.add(ticket)
            s.flush()
            mail = OutgoingMail(
                to=[self.quality_email], cc=[profile.email], subject=self._subject(ticket), body=self._body(ticket)
            )
            msg_id = self.transport.send(mail)
            ticket.message_id, ticket.status, ticket.sent_at = msg_id, "sent", utcnow()
            s.add(
                MailRow(
                    ticket_id=ticket.id,
                    direction="out",
                    message_id=msg_id,
                    sender=self.transport.address,
                    recipients=[*mail.to, *mail.cc],
                    subject=mail.subject,
                    body=mail.body,
                )
            )
        return ticket

    def _subject(self, ticket: TicketRow) -> str:
        short = ticket.question if len(ticket.question) <= 70 else ticket.question[:67] + "..."
        return f"[{ticket.code}] Вопрос по регламентам: {short}"

    def _body(self, ticket: TicketRow) -> str:
        dep = self.passport.department(ticket.department).name if ticket.department else "не указано"
        lines = [
            "Здравствуйте, коллеги из службы качества!",
            "",
            "Сотрудник задал вопрос агенту по регламентам, но в действующих регламентах ответа нет.",
            "",
            f"Вопрос: {ticket.question}",
        ]
        if ticket.context:
            lines += ["", f"Уточнения из диалога: {ticket.context}"]
        lines += [
            "",
            f"Сотрудник: {ticket.employee_name} ({ticket.employee_email}), подразделение: {dep}.",
            "",
            "Пожалуйста, ответьте на это письмо «Ответить всем»: агент сам найдёт в переписке финальный ответ,",
            "сообщит его сотруднику и добавит в базу знаний как разъяснение службы качества.",
            "Если ответить должен владелец процесса - просто добавьте его в копию. Метка «#ответ» в письме -",
            "явный финальный ответ, «#черновик» - письмо не будет учтено.",
            "",
            f"Обращение {ticket.code}. Агент по регламентам MORE TECH.",
        ]
        return "\n".join(lines)

    # ---------- чтение ответов ----------

    def poll(self) -> PollReport:
        incoming = self.transport.fetch_new()
        matched = 0
        published: list[int] = []
        for mail in incoming:
            ticket_id = self._match_ticket(mail)
            if ticket_id is None:
                log.info("письмо %s не относится к обращениям", mail.message_id)
                continue
            matched += 1
            note_id = self._process(ticket_id, mail)
            if note_id is not None:
                published.append(note_id)
        return PollReport(received=len(incoming), matched=matched, published_notes=published)

    def _match_ticket(self, mail: IncomingMail) -> int | None:
        code = CODE_RE.search(mail.subject)
        if code:
            return int(code.group(1))
        ids = [i for i in [mail.in_reply_to, *mail.references] if i]
        if not ids:
            return None
        with self.sessions() as s:
            row = s.scalars(select(MailRow).where(MailRow.message_id.in_(ids), MailRow.ticket_id.is_not(None))).first()
            return row.ticket_id if row else None

    def _role(self, s: Session, ticket: TicketRow, sender: str) -> SenderRole:
        if sender == ticket.employee_email.lower():
            return SenderRole.EMPLOYEE
        if any(sender == a or (a.startswith("@") and sender.endswith(a)) for a in self.authorized):
            return SenderRole.QUALITY
        # Участник, которого служба качества сама добавила в переписку (владелец процесса)
        quality_mails = s.scalars(
            select(MailRow).where(MailRow.ticket_id == ticket.id, MailRow.direction == "in")
        ).all()
        for m in quality_mails:
            if self._is_authorized(m.sender) and sender in m.recipients:
                return SenderRole.ADDED_BY_QUALITY
        return SenderRole.UNKNOWN

    def _is_authorized(self, sender: str) -> bool:
        return any(sender == a or (a.startswith("@") and sender.endswith(a)) for a in self.authorized)

    def _process(self, ticket_id: int, mail: IncomingMail) -> int | None:
        with self.sessions.begin() as s:
            ticket = s.get(TicketRow, ticket_id)
            if ticket is None or s.scalars(select(MailRow).where(MailRow.message_id == mail.message_id)).first():
                return None
            role = self._role(s, ticket, mail.sender)
            thread = [
                Message(sender=m.sender, body=m.body[:1500])
                for m in s.scalars(select(MailRow).where(MailRow.ticket_id == ticket.id).order_by(MailRow.id))
            ]
            row = MailRow(
                ticket_id=ticket.id,
                direction="in",
                message_id=mail.message_id,
                in_reply_to=mail.in_reply_to,
                sender=mail.sender,
                recipients=mail.recipients,
                subject=mail.subject,
                body=mail.body,
                received_at=mail.received_at,
            )
            s.add(row)
            ctx = SkillContext(llm=self.llm)
            try:
                verdict = self.classifier.run(
                    ClassifyInput(
                        question=ticket.question,
                        thread=thread,
                        message=Message(sender=mail.sender, body=mail.body),
                        sender_role=role,
                    ),
                    ctx,
                )
            except LLMError:
                log.exception("не удалось разобрать письмо %s", mail.message_id)
                row.classification = "error"
                return None
            finally:
                self.on_usage(ctx)
            row.classification = verdict.kind.value
            if verdict.kind is ReplyKind.QUESTION_TO_EMPLOYEE:
                self._notify(
                    s,
                    ticket,
                    f"Служба качества задала уточняющий вопрос по обращению {ticket.code} - "
                    f"ответьте, пожалуйста, на письмо в почте.",
                )
                return None
            if verdict.kind is not ReplyKind.FINAL_ANSWER:
                return None
            candidates = self._candidates(s, ticket.candidate_clause_ids)
            ticket_snapshot = (ticket.id, ticket.question, ticket.context, ticket.department)
        return self._publish(ticket_snapshot, verdict.answer_text, mail.sender, candidates)

    def _candidates(self, s: Session, clause_ids: list[str]) -> list[CandidateClause]:
        titles = {d.id: d.title for d in s.scalars(select(DocumentRow))}
        rows = s.scalars(select(ClauseRow).where(ClauseRow.id.in_(clause_ids))).all()
        return [CandidateClause(id=c.id, ref=clause_ref(c.number, titles.get(c.doc_id, "")), text=c.text) for c in rows]

    def _publish(
        self, ticket: tuple[int, str, str, str | None], answer: str, expert: str, candidates: list[CandidateClause]
    ) -> int | None:
        ticket_id, question, context, department = ticket
        ctx = SkillContext(llm=self.llm)
        try:
            clar = self.extractor.run(
                ExtractInput(
                    question="\n".join(filter(None, [question, context])),
                    expert_answer=answer,
                    departments={d.id: d.name for d in self.passport.departments},
                    employee_department=department,
                    candidate_clauses=candidates,
                ),
                ctx,
            )
        except LLMError:
            log.exception("не удалось оформить разъяснение по обращению %s", ticket_id)
            return None
        finally:
            self.on_usage(ctx)
        with self.sessions() as s:
            previous = list(
                s.scalars(
                    select(NoteRow).where(NoteRow.ticket_id == ticket_id, NoteRow.status.in_(("published", "disputed")))
                )
            )
        same_expert = [n for n in previous if n.expert == expert]
        other_experts = [n for n in previous if n.expert != expert]
        disputed = [n for n in other_experts if answers_differ(n.answer, clar.answer)]
        for old in same_expert:
            self.kb.set_note_status(old.id, "retired", "заменено исправленным ответом того же эксперта")
        for old in disputed:
            self.kb.set_note_status(old.id, "disputed", f"другой эксперт ({expert}) ответил иначе")
        note = self.kb.add_note(
            question=clar.canonical_question,
            answer=clar.answer,
            department_ids=clar.department_ids,
            related_clause_ids=clar.related_clause_ids,
            keywords=clar.keywords,
            expert=expert,
            ticket_id=ticket_id,
            status="disputed" if disputed else "published",
            review_reason=f"ответ расходится с ответом {disputed[0].expert}" if disputed else "",
        )
        with self.sessions.begin() as s:
            t = s.get(TicketRow, ticket_id)
            if t is None:
                raise RuntimeError("обращение исчезло во время публикации ответа")
            row = s.get(NoteRow, note.id)
            if row is not None and same_expert:
                row.supersedes_id = same_expert[-1].id
            t.status, t.answered_at, t.note_id = "answered", utcnow(), note.id
            if disputed:
                text = (
                    f"По обращению {t.code} эксперты службы качества ответили по-разному:\n\n"
                    + "\n\n".join(f"{n.expert}: {n.answer}" for n in [*disputed, row or note])
                    + "\n\nОба ответа сохранены с пометкой - служба качества выберет итоговый."
                )
            else:
                text = (
                    f"Служба качества ответила на ваш вопрос (обращение {t.code}):\n\n{clar.answer}\n\n"
                    "Ответ добавлен в базу знаний - на похожие вопросы агент теперь ответит сам."
                )
            self._notify(s, t, text)
        return note.id

    def _notify(self, s: Session, ticket: TicketRow, text: str) -> None:
        reply = AgentReply(
            kind=ChatKind.ESCALATION_SENT,
            text=text,
            ticket=TicketView(code=ticket.code, status=ticket.status, quality_email=self.quality_email),
        )
        s.add(
            TurnRow(
                conversation_id=ticket.conversation_id,
                role="agent",
                text=text,
                payload=reply.model_dump(mode="json"),
                outcome="quality_reply",
            )
        )

    def open_tickets(self) -> list[TicketRow]:
        with self.sessions() as s:
            return list(
                s.scalars(select(TicketRow).where(or_(TicketRow.status == "sent", TicketRow.status == "draft")))
            )
