"""Регламент с якорями пунктов: ссылка из ответа открывает нужный пункт."""

from __future__ import annotations

import html

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from reglament_agent.adapters.db import ClauseRow, DocumentRow
from reglament_agent.api.deps import ContainerDep

router = APIRouter(prefix="/api/documents", tags=["документы"])

_STYLE = (
    "body{font:16px/1.55 system-ui,sans-serif;max-width:860px;margin:32px auto;padding:0 16px;color:#1d2433}"
    "h2{margin-top:28px}:target{background:#fff4c2;outline:6px solid #fff4c2}"
)


@router.get("/{doc_id}", response_class=HTMLResponse)
def document(doc_id: str, c: ContainerDep) -> str:
    with c.sessions() as s:
        doc = s.get(DocumentRow, doc_id)
        if doc is None:
            raise HTTPException(404, "Документ не найден")
        rows = s.scalars(
            select(ClauseRow).where(ClauseRow.doc_id == doc_id, ClauseRow.active.is_(True)).order_by(ClauseRow.ord)
        ).all()
        title = html.escape(doc.title)
        parts = [f"<!doctype html><meta charset=utf-8><title>{title}</title><style>{_STYLE}</style><h1>{title}</h1>"]
        for r in rows:
            body = "<br>".join(html.escape(line) for line in r.text.split("\n"))
            tag = "h2" if "." not in r.number else "p"
            num = html.escape(r.number)
            parts.append(f'<{tag} id="{num}"><b>{num}.</b> {body}</{tag}>')
    return "".join(parts)
