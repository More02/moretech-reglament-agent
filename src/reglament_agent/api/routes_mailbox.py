"""Переписка со службой качества в кабинете.

Показывает письма по обращениям при любом почтовом бэкенде. Если почта агента работает в режиме ``memory``
(стенд без настоящих ящиков), здесь же эксперт службы качества может ответить на письмо - ответ проходит тот же
путь, что и письмо из IMAP: определение прав отправителя, финальности, разъяснение в базе знаний, уведомление
сотрудника в чате.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from reglament_agent.adapters.db import MailRow, TicketRow
from reglament_agent.adapters.mail import IncomingMail, MemoryMailbox
from reglament_agent.api.deps import ContainerDep, admin_only

router = APIRouter(prefix="/api/admin/mail", tags=["почта службы качества"], dependencies=[Depends(admin_only)])


class ExpertReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_code: str = Field(min_length=3, max_length=20)
    sender: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=2, max_length=10_000)


@router.get("")
def threads(c: ContainerDep) -> dict[str, Any]:
    with c.sessions() as s:
        tickets = s.scalars(select(TicketRow).order_by(TicketRow.id.desc()).limit(50)).all()
        out = []
        for t in tickets:
            mails = s.scalars(select(MailRow).where(MailRow.ticket_id == t.id).order_by(MailRow.id)).all()
            out.append(
                {
                    "code": t.code,
                    "question": t.question,
                    "status": t.status,
                    "employee": t.employee_name,
                    "employee_email": t.employee_email,
                    "created_at": t.created_at.isoformat(),
                    "messages": [
                        {
                            "direction": m.direction,
                            "sender": m.sender,
                            "recipients": m.recipients,
                            "subject": m.subject,
                            "body": m.body,
                            "classification": m.classification,
                            "at": m.received_at.isoformat(),
                        }
                        for m in mails
                    ],
                }
            )
    return {
        "demo": isinstance(c.mail_transport, MemoryMailbox),
        "agent_address": c.mail_transport.address,
        "quality_email": c.settings.quality_email,
        "threads": out,
    }


@router.post("/reply")
def reply(body: ExpertReply, c: ContainerDep) -> dict[str, Any]:
    box = c.mail_transport
    if not isinstance(box, MemoryMailbox):
        raise HTTPException(409, "Почта агента подключена к настоящему ящику - отвечайте из почтового клиента")
    with c.sessions() as s:
        digits = "".join(ch for ch in body.ticket_code if ch.isdigit())
        ticket = s.get(TicketRow, int(digits)) if digits else None
        if ticket is None:
            raise HTTPException(404, "Обращение не найдено")
        last = s.scalars(select(MailRow).where(MailRow.ticket_id == ticket.id).order_by(MailRow.id.desc())).first()
        subject = f"Re: {last.subject}" if last else f"Re: [{ticket.code}]"
        in_reply_to = last.message_id if last else ""
        recipients = [box.address, ticket.employee_email]
    box.deliver(
        IncomingMail(
            message_id=f"<{uuid.uuid4().hex}@quality.demo>",
            sender=body.sender.strip(),
            recipients=recipients,
            subject=subject,
            body=body.body,
            in_reply_to=in_reply_to,
            references=[in_reply_to] if in_reply_to else [],
        )
    )
    report = c.mail.poll()
    return {"received": report.received, "matched": report.matched, "published_notes": report.published_notes}
