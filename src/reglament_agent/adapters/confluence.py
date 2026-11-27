"""Источник регламентов из Atlassian Confluence (REST API): страницы пространства → дерево пунктов.

У заказчика регламенты лежат в Confluence без дополнений (ответ в чате задачи). Страница соответствует документу
паспорта по ``confluence_page_id`` или по точному названию. Версия страницы сохраняется в отпечатке документа,
поэтому изменённые пункты и связанные разъяснения находятся автоматически при переиндексации.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from reg_parse import ParsedDocument, build_document, read_html
from reglament_agent.passport import DocumentDef, Passport

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConfluencePage:
    id: str
    title: str
    version: int
    html: str


class ConfluenceSource:
    def __init__(self, base_url: str, token: str, space: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self.space = space
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30,
            transport=transport,
        )

    def pages(self) -> list[ConfluencePage]:
        out: list[ConfluencePage] = []
        start = 0
        while True:
            resp = self._client.get(
                "/rest/api/content",
                params={
                    "spaceKey": self.space,
                    "type": "page",
                    "expand": "body.storage,version",
                    "limit": 50,
                    "start": start,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            for r in data.get("results", []):
                out.append(
                    ConfluencePage(
                        id=str(r["id"]),
                        title=r["title"],
                        version=int(r.get("version", {}).get("number", 0)),
                        html=r.get("body", {}).get("storage", {}).get("value", ""),
                    )
                )
            if data.get("size", 0) < data.get("limit", 50) or not data.get("results"):
                return out
            start += data.get("limit", 50)

    def documents(self, passport: Passport) -> list[tuple[DocumentDef, ParsedDocument]]:
        """Документы паспорта, найденные в пространстве. Заголовок страницы - название документа."""
        by_id = {p.id: p for p in self.pages()}
        by_title = {p.title.strip().lower(): p for p in by_id.values()}
        result: list[tuple[DocumentDef, ParsedDocument]] = []
        for meta in passport.documents:
            page = by_id.get(meta.confluence_page_id or "") or by_title.get(meta.title.strip().lower())
            if page is None:
                log.warning("страница для документа %s не найдена в пространстве %s", meta.id, self.space)
                continue
            parsed = build_document(meta.id, read_html(page.html), title=page.title)
            result.append((meta, parsed))
        return result
