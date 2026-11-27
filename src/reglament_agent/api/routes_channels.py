"""Канал-вебхук для корпоративных мессенджеров (DION и др.): один чат = один диалог агента."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select

from reglament_agent.adapters.db import ConversationRow
from reglament_agent.api.deps import ContainerDep, rate_limited
from reglament_agent.api.schemas import WebhookMessage
from reglament_agent.container import Container
from reglament_agent.domain import AgentReply

router = APIRouter(prefix="/api/channels", tags=["каналы"])


@router.post("/webhook", dependencies=[Depends(rate_limited)])
def webhook(body: WebhookMessage, c: ContainerDep) -> dict[str, Any]:
    conv_id = channel_conversation(c, body)
    reply = c.agent.choose(conv_id, body.option_id) if body.option_id else c.agent.ask(conv_id, body.text)
    return {"text": render_plain(reply), "buttons": [o.model_dump() for o in reply.options]}


def channel_conversation(c: Container, body: WebhookMessage) -> str:
    key = f"channel:{body.chat_id}"
    with c.sessions.begin() as s:
        existing = s.scalars(select(ConversationRow).where(ConversationRow.channel_key == key)).first()
        if existing is not None:
            return existing.id
        conv = ConversationRow(profile=body.user.model_dump(), state={}, channel_key=key)
        s.add(conv)
        s.flush()
        return conv.id


def render_plain(reply: AgentReply) -> str:
    """Ответ простым текстом для мессенджеров без богатой разметки."""
    lines = [reply.text]
    for v in reply.variants:
        lines.append(f"\n{v.department_name}:" + (f" {v.lead}" if v.lead else ""))
        lines += [f"- {cl.text} ({cl.source_title})" for cl in v.claims]
    if reply.missing_documents:
        lines.append("\nРегламенты ссылаются на документы, которых нет в базе: " + "; ".join(reply.missing_documents))
    return "\n".join(lines).strip()
