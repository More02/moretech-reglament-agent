"""Сквозные сценарии заказчика на тестовой модели: ответ, уточнение, эксперт → база знаний → повторный ответ."""

from __future__ import annotations

from reglament_agent.adapters.mail import IncomingMail, MemoryMailbox
from reglament_agent.container import Container
from reglament_agent.domain import Profile, ReplyKind

EMPLOYEE = Profile(name="Иванов Иван", email="ivanov@corp.test")


def test_s1_answer_with_citation_for_profile_department(app: tuple[Container, MemoryMailbox]) -> None:
    c, _ = app
    conv = c.agent.start(EMPLOYEE.model_copy(update={"department": "alpha"}))
    reply = c.agent.ask(conv, "Можно ли подать бюджетную оценку в конкурс?")
    assert reply.kind is ReplyKind.ANSWER
    assert "по вашему профилю" in reply.text
    claim = reply.variants[0].claims[0]
    assert claim.source_id == "alpha-doc:1.2"
    assert "RFI" in claim.quote
    assert reply.usage.llm_calls == 2


def test_s2_clarification_then_instant_choice(app: tuple[Container, MemoryMailbox]) -> None:
    c, _ = app
    conv = c.agent.start(EMPLOYEE)
    reply = c.agent.ask(conv, "Как часто РП обновляет реестр рисков?")
    assert reply.kind is ReplyKind.CLARIFY
    assert {o.id for o in reply.options} >= {"dep:alpha", "dep:beta", "all", "complex"}
    chosen = c.agent.choose(conv, "dep:beta")
    assert chosen.kind is ReplyKind.ANSWER
    assert chosen.usage.llm_calls == 0
    assert "месяц" in chosen.variants[0].claims[0].quote


def test_s2_typed_answer_and_dont_know(app: tuple[Container, MemoryMailbox]) -> None:
    c, _ = app
    conv = c.agent.start(EMPLOYEE)
    c.agent.ask(conv, "Как часто РП обновляет реестр рисков?")
    all_variants = c.agent.ask(conv, "не знаю")
    assert all_variants.kind is ReplyKind.ANSWER
    assert [v.department_id for v in all_variants.variants] == ["alpha", "beta"]


def test_department_named_in_question_skips_clarification(app: tuple[Container, MemoryMailbox]) -> None:
    c, _ = app
    conv = c.agent.start(EMPLOYEE)
    reply = c.agent.ask(conv, "Как часто РП в Бета обновляет реестр рисков?")
    assert reply.kind is ReplyKind.ANSWER
    assert [v.department_id for v in reply.variants] == ["beta"]


def test_s3_escalation_expert_answer_and_reuse(app: tuple[Container, MemoryMailbox]) -> None:
    c, mailbox = app
    conv = c.agent.start(EMPLOYEE.model_copy(update={"department": "alpha"}))
    reply = c.agent.ask(conv, "Компенсируют ли такси в командировке в выходной день?")
    assert reply.kind is ReplyKind.NOT_FOUND
    sent = c.agent.choose(conv, "escalate")
    assert sent.kind is ReplyKind.ESCALATION_SENT
    assert sent.ticket is not None
    msg_id, mail = mailbox.sent[-1]
    assert mail.to == ["quality@corp.test"]
    assert mail.cc == ["ivanov@corp.test"]
    assert sent.ticket.code in mail.subject

    mailbox.deliver(
        IncomingMail(
            message_id="<r1@corp.test>",
            sender="quality@corp.test",
            recipients=["agent@corp.test", "ivanov@corp.test"],
            subject=f"Re: {mail.subject}",
            body="Добрый день! Такси в командировке в выходной день компенсируется по согласованию с руководителем проекта.",
            in_reply_to=msg_id,
        )
    )
    report = c.mail.poll()
    assert report.matched == 1
    assert len(report.published_notes) == 1

    conv2 = c.agent.start(Profile(name="Петров", email="petrov@corp.test", department="alpha"))
    again = c.agent.ask(conv2, "Оплачивается ли такси в командировке в выходной?")
    assert again.kind is ReplyKind.ANSWER
    assert again.variants[0].claims[0].from_quality


def test_employee_reply_is_not_an_expert_answer(app: tuple[Container, MemoryMailbox]) -> None:
    c, mailbox = app
    conv = c.agent.start(EMPLOYEE.model_copy(update={"department": "alpha"}))
    c.agent.ask(conv, "Компенсируют ли такси в командировке в выходной день?")
    sent = c.agent.choose(conv, "escalate")
    assert sent.ticket is not None
    mailbox.deliver(
        IncomingMail(
            message_id="<e1@corp.test>",
            sender="ivanov@corp.test",
            recipients=["quality@corp.test"],
            subject=f"Re: [{sent.ticket.code}] вопрос",
            body="Я думаю, что такси точно компенсируют всегда.",
        )
    )
    assert c.mail.poll().published_notes == []


def test_out_of_scope_and_off_task(app: tuple[Container, MemoryMailbox]) -> None:
    c, mailbox = app
    conv = c.agent.start(EMPLOYEE)
    assert c.agent.ask(conv, "Какую премию я получу за сделку?").kind is ReplyKind.OUT_OF_SCOPE
    assert c.agent.ask(conv, "Какой сегодня курс доллара?").kind is ReplyKind.OFF_TASK
    assert mailbox.sent == []


def test_changed_clause_flags_linked_note(app: tuple[Container, MemoryMailbox]) -> None:
    c, _ = app
    note = c.kb.add_note(
        question="q",
        answer="a",
        department_ids=["alpha"],
        related_clause_ids=["alpha-doc:2.1"],
        keywords=[],
        expert="quality@corp.test",
        ticket_id=None,
    )
    parsed = c.kb.parse_directory(c.settings.regulations_dir)
    meta, doc = parsed[0]
    changed = doc.model_copy(
        update={
            "clauses": tuple(
                cl.model_copy(update={"text": cl.text.replace("1 раза в неделю", "2 раз в неделю")})
                for cl in doc.clauses
            )
        }
    )
    report = c.kb.ingest([(meta, changed)])
    assert "alpha-doc:2.1" in report.changed_clauses
    assert report.notes_flagged == [note.id]


def _escalated(c: Container, mailbox: MemoryMailbox) -> tuple[str, str]:
    conv = c.agent.start(EMPLOYEE.model_copy(update={"department": "alpha"}))
    c.agent.ask(conv, "Компенсируют ли такси в командировке в выходной день?")
    sent = c.agent.choose(conv, "escalate")
    assert sent.ticket is not None
    msg_id, mail = mailbox.sent[-1]
    return msg_id, mail.subject


def _reply(mailbox: MemoryMailbox, mid: str, sender: str, subject: str, body: str, parent: str) -> None:
    mailbox.deliver(
        IncomingMail(
            message_id=mid,
            sender=sender,
            recipients=["agent@corp.test"],
            subject=f"Re: {subject}",
            body=body,
            in_reply_to=parent,
        )
    )


def test_two_experts_disagree_both_answers_kept_and_flagged(app: tuple[Container, MemoryMailbox]) -> None:
    c, mailbox = app
    c.mail.authorized.append("@corp.test")
    msg_id, subject = _escalated(c, mailbox)
    _reply(
        mailbox,
        "<a@x>",
        "quality@corp.test",
        subject,
        "Такси в выходной день в командировке компенсируется полностью.",
        msg_id,
    )
    _reply(
        mailbox,
        "<b@x>",
        "head@corp.test",
        subject,
        "Нет, компенсация такси возможна только до 2000 рублей по чеку и с согласования директора.",
        msg_id,
    )
    report = c.mail.poll()
    assert len(report.published_notes) == 2
    summary = c.analytics.summary()
    assert len(summary["notes"]["needs_review"]) == 0
    from sqlalchemy import select

    from reglament_agent.adapters.db import NoteRow

    with c.sessions() as s:
        statuses = sorted(n.status for n in s.scalars(select(NoteRow)))
    assert statuses == ["disputed", "disputed"]


def test_same_expert_correction_supersedes(app: tuple[Container, MemoryMailbox]) -> None:
    c, mailbox = app
    msg_id, subject = _escalated(c, mailbox)
    _reply(
        mailbox,
        "<a@x>",
        "quality@corp.test",
        subject,
        "Такси в выходной день в командировке компенсируется полностью.",
        msg_id,
    )
    _reply(
        mailbox,
        "<b@x>",
        "quality@corp.test",
        subject,
        "Поправка: такси компенсируется только при согласовании руководителя проекта.",
        msg_id,
    )
    c.mail.poll()
    from sqlalchemy import select

    from reglament_agent.adapters.db import NoteRow

    with c.sessions() as s:
        statuses = sorted(n.status for n in s.scalars(select(NoteRow)))
    assert statuses == ["published", "retired"]


def test_choosing_other_department_than_profile_composes_it(app: tuple[Container, MemoryMailbox]) -> None:
    c, _ = app
    conv = c.agent.start(EMPLOYEE.model_copy(update={"department": "alpha"}))
    first = c.agent.ask(conv, "Как часто РП обновляет реестр рисков?")
    assert [v.department_id for v in first.variants] == ["alpha"]
    other = c.agent.ask(conv, "Бета")
    assert other.kind is ReplyKind.ANSWER
    assert [v.department_id for v in other.variants] == ["beta"]


def test_escalate_without_pending_uses_last_question(app: tuple[Container, MemoryMailbox]) -> None:
    c, mailbox = app
    conv = c.agent.start(EMPLOYEE.model_copy(update={"department": "alpha"}))
    c.agent.ask(conv, "Компенсируют ли такси в командировке в выходной день?")
    sent = c.agent.choose(conv, "escalate")
    assert sent.kind is ReplyKind.ESCALATION_SENT
    assert "такси" in mailbox.sent[-1][1].body
