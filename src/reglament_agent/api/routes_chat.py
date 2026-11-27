"""Чат сотрудника."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from reglament_agent.adapters.db import ClauseRow, ConversationRow, TurnRow
from reglament_agent.api.deps import ContainerDep, rate_limited
from reglament_agent.api.schemas import AskMessage, ChooseOption, Rating, StartConversation
from reglament_agent.domain import AgentReply

router = APIRouter(prefix="/api", tags=["чат"])


@router.get("/health")
def health(c: ContainerDep) -> dict[str, Any]:
    with c.sessions() as s:
        clauses = len(s.scalars(select(ClauseRow.id).where(ClauseRow.active.is_(True))).all())
    return {"status": "ok", "clauses": clauses, "model": c.settings.llm_model, "fake_llm": c.settings.llm_fake}


@router.get("/meta")
def meta(c: ContainerDep) -> dict[str, Any]:
    p = c.passport
    return {
        "company": p.company,
        "assistant": p.assistant_name,
        "departments": [{"id": d.id, "name": d.name, "full_name": d.full_name} for d in p.departments],
        "documents": [{"id": d.id, "title": d.title, "department": d.department} for d in p.documents],
        "demo_profiles": [dp.model_dump() for dp in p.demo_profiles],
        "quality_email": c.settings.quality_email,
    }


@router.post("/conversations")
def start(body: StartConversation, c: ContainerDep) -> dict[str, str]:
    return {"id": c.agent.start(body.profile)}


@router.post("/conversations/{conv_id}/messages", dependencies=[Depends(rate_limited)])
def ask(conv_id: str, body: AskMessage, c: ContainerDep) -> AgentReply:
    try:
        return c.agent.ask(conv_id, body.text.strip())
    except KeyError as exc:
        raise HTTPException(404, "Диалог не найден") from exc


@router.post("/conversations/{conv_id}/options", dependencies=[Depends(rate_limited)])
def choose(conv_id: str, body: ChooseOption, c: ContainerDep) -> AgentReply:
    try:
        return c.agent.choose(conv_id, body.option_id)
    except KeyError as exc:
        raise HTTPException(404, "Диалог не найден") from exc


@router.get("/conversations/{conv_id}/turns")
def turns(conv_id: str, c: ContainerDep, after: int = 0) -> list[dict[str, Any]]:
    """Новые реплики агента после ``after`` - например, ответ эксперта, пришедший по почте."""
    with c.sessions() as s:
        if s.get(ConversationRow, conv_id) is None:
            raise HTTPException(404, "Диалог не найден")
        rows = s.scalars(
            select(TurnRow)
            .where(TurnRow.conversation_id == conv_id, TurnRow.id > after, TurnRow.role == "agent")
            .order_by(TurnRow.id)
        ).all()
        return [{"id": t.id, "reply": t.payload} for t in rows]


@router.post("/turns/{turn_id}/rating")
def rate(turn_id: int, body: Rating, c: ContainerDep) -> dict[str, str]:
    c.agent.rate(turn_id, body.rating)
    return {"status": "ok"}
