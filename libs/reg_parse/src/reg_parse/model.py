"""Модель разобранного регламента."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, Field


class Clause(BaseModel):
    """Пункт регламента. Раздел верхнего уровня (``8``) - тоже пункт, его текст - заголовок раздела."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str
    number: str = Field(description="Номер пункта как в документе: '8', '8.4', '20.2.1'; '0' - вводная часть")
    heading: str = Field(description="Первая строка пункта без номера")
    text: str = Field(description="Полный текст пункта с подпунктами-перечислениями, без номера")
    parent: str | None = None
    path: tuple[str, ...] = Field(default=(), description="Заголовки разделов-предков сверху вниз")
    order: int = Field(description="Порядковый номер пункта в документе")

    @property
    def clause_id(self) -> str:
        return f"{self.doc_id}:{self.number}"

    @property
    def level(self) -> int:
        return self.number.count(".") + 1

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]


class DocReference(BaseModel):
    """Ссылка из пункта на пункт этого же документа или на другой документ."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    clause_id: str
    kind: str = Field(description="'clause' - ссылка на пункт, 'document' - на другой документ")
    target: str
    exists: bool | None = Field(default=None, description="Для ссылки на пункт: есть ли такой пункт в документе")


class ParsedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str
    title: str
    clauses: tuple[Clause, ...]
    references: tuple[DocReference, ...] = ()

    def clause(self, number: str) -> Clause | None:
        return next((c for c in self.clauses if c.number == number), None)

    @property
    def fingerprint(self) -> str:
        joined = "\n".join(c.fingerprint for c in self.clauses)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
