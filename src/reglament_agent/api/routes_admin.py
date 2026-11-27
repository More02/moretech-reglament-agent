"""Кабинет службы качества: аналитика, разъяснения, обращения, переиндексация, садовник, отчёт тестов."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from reglament_agent.adapters.db import NoteRow, TicketRow
from reglament_agent.api.deps import ContainerDep, admin_only
from reglament_agent.api.schemas import NoteStatus
from reglament_agent.config import ROOT

router = APIRouter(prefix="/api/admin", tags=["кабинет службы качества"], dependencies=[Depends(admin_only)])


@router.get("/analytics")
def analytics(c: ContainerDep, days: int = 30) -> dict[str, Any]:
    return c.analytics.summary(days)


@router.get("/notes")
def notes(c: ContainerDep) -> list[dict[str, Any]]:
    with c.sessions() as s:
        return [
            {
                "id": n.id,
                "question": n.canonical_question,
                "answer": n.answer,
                "status": n.status,
                "reason": n.review_reason,
                "expert": n.expert,
                "departments": n.department_ids,
                "clauses": n.related_clause_ids,
                "created_at": n.created_at.isoformat(),
                "ticket_id": n.ticket_id,
            }
            for n in s.scalars(select(NoteRow).order_by(NoteRow.id.desc()))
        ]


@router.patch("/notes/{note_id}")
def set_note(note_id: int, body: NoteStatus, c: ContainerDep) -> dict[str, str]:
    try:
        c.kb.set_note_status(note_id, body.status, body.reason)
    except KeyError as exc:
        raise HTTPException(404, "Разъяснение не найдено") from exc
    return {"status": "ok"}


@router.get("/tickets")
def tickets(c: ContainerDep) -> list[dict[str, Any]]:
    with c.sessions() as s:
        return [
            {
                "code": t.code,
                "question": t.question,
                "status": t.status,
                "employee": t.employee_name,
                "created_at": t.created_at.isoformat(),
                "note_id": t.note_id,
            }
            for t in s.scalars(select(TicketRow).order_by(TicketRow.id.desc()))
        ]


@router.post("/reindex")
def reindex(c: ContainerDep) -> dict[str, Any]:
    r = c.kb.ingest(c.kb.parse_directory(c.settings.regulations_dir))
    return {
        "documents": r.documents,
        "clauses": r.clauses,
        "changed": r.changed_clauses,
        "removed": r.removed_clauses,
        "notes_flagged": r.notes_flagged,
    }


@router.post("/mail/poll")
def poll(c: ContainerDep) -> dict[str, Any]:
    r = c.mail.poll()
    return {"received": r.received, "matched": r.matched, "published_notes": r.published_notes}


@router.post("/gardener")
def gardener(c: ContainerDep, send_digest: bool = False) -> dict[str, Any]:
    r = c.gardener.run(send_digest=send_digest)
    return {
        "clusters": [cl.model_dump() for cl in r.clusters],
        "notes_need_review": r.notes_need_review,
        "digest_sent": r.digest_sent,
    }


@router.get("/eval")
def eval_report() -> dict[str, Any]:
    path = ROOT / "evals" / "reports" / "latest.json"
    if not path.exists():
        return {}
    report: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return report
