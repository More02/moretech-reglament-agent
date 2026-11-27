"""База знаний: загрузка регламентов, разъяснения службы качества, отслеживание изменений, сборка поискового индекса."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from reg_parse import ParsedDocument, build_document, read_docx, read_html
from reglament_agent.adapters.db import ClauseRow, DocumentRow, NoteRow, ReferenceRow, utcnow
from reglament_agent.adapters.embeddings import Embedder, from_bytes, to_bytes
from reglament_agent.passport import DocumentDef, Passport
from reglament_agent.services.retrieval import HybridIndex, Unit

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestReport:
    documents: int
    clauses: int
    changed_clauses: list[str]
    removed_clauses: list[str]
    notes_flagged: list[int]


def clause_ref(number: str, doc_title: str) -> str:
    return f"п. {number}, «{doc_title}»" if number != "0" else f"вводная часть, «{doc_title}»"


class KnowledgeBase:
    def __init__(
        self, sessions: sessionmaker[Session], passport: Passport, embedder: Embedder, index: HybridIndex
    ) -> None:
        self.sessions = sessions
        self.passport = passport
        self.embedder = embedder
        self.index = index

    # ---------- загрузка регламентов ----------

    def parse_directory(self, directory: Path) -> list[tuple[DocumentDef, ParsedDocument]]:
        parsed: list[tuple[DocumentDef, ParsedDocument]] = []
        for doc in self.passport.documents:
            path = directory / doc.file
            if not path.exists():
                log.warning("документ %s не найден в %s", doc.file, directory)
                continue
            paras = read_html(path.read_text(encoding="utf-8")) if path.suffix == ".html" else read_docx(path)
            parsed.append((doc, build_document(doc.id, paras)))
        return parsed

    def ingest(self, documents: Iterable[tuple[DocumentDef, ParsedDocument]]) -> IngestReport:
        """Обновляет пункты документов. Изменённые пункты → связанные разъяснения на перепроверку."""
        docs = list(documents)
        changed: list[str] = []
        removed: list[str] = []
        total = 0
        with self.sessions.begin() as s:
            for meta, parsed in docs:
                old = {c.id: c for c in s.scalars(select(ClauseRow).where(ClauseRow.doc_id == meta.id))}
                if s.get(DocumentRow, meta.id) is None:
                    s.add(
                        DocumentRow(
                            id=meta.id,
                            title=parsed.title,
                            department=meta.department,
                            source=meta.file,
                            fingerprint=parsed.fingerprint,
                        )
                    )
                row = s.get(DocumentRow, meta.id)
                if row is None:
                    raise RuntimeError("нарушен инвариант: row отсутствует")
                row.title, row.fingerprint, row.updated_at = parsed.title, parsed.fingerprint, utcnow()
                s.flush()
                new_ids = {c.clause_id for c in parsed.clauses}
                texts = [self._search_text(meta, parsed.title, c.number, c.path, c.text) for c in parsed.clauses]
                vectors = self.embedder.embed(texts) if texts else np.zeros((0, 1), dtype=np.float32)
                for clause, vec in zip(parsed.clauses, vectors, strict=True):
                    prev = old.get(clause.clause_id)
                    if prev is not None and prev.fingerprint != clause.fingerprint:
                        changed.append(clause.clause_id)
                    s.merge(
                        ClauseRow(
                            id=clause.clause_id,
                            doc_id=meta.id,
                            number=clause.number,
                            heading=clause.heading,
                            text=clause.text,
                            path=list(clause.path),
                            parent=clause.parent,
                            ord=clause.order,
                            department=meta.department,
                            process=meta.process_of(clause.number),
                            fingerprint=clause.fingerprint,
                            embedding=to_bytes(vec),
                            active=True,
                        )
                    )
                for gone in set(old) - new_ids:
                    removed.append(gone)
                    old[gone].active = False
                s.execute(delete(ReferenceRow).where(ReferenceRow.clause_id.like(f"{meta.id}:%")))
                for ref in parsed.references:
                    s.add(ReferenceRow(clause_id=ref.clause_id, kind=ref.kind, target=ref.target, exists=ref.exists))
                total += len(parsed.clauses)
            flagged = self._flag_notes(s, set(changed) | set(removed))
        self.rebuild_index()
        return IngestReport(len(docs), total, changed, removed, flagged)

    def _search_text(self, meta: DocumentDef, title: str, number: str, path: Iterable[str], text: str) -> str:
        dep = self.passport.department(meta.department)
        return f"{title}. {dep.name}. {' / '.join(path)}\n{number}. {text}"

    @staticmethod
    def _flag_notes(s: Session, touched: set[str]) -> list[int]:
        if not touched:
            return []
        flagged: list[int] = []
        for note in s.scalars(select(NoteRow).where(NoteRow.status == "published")):
            hit = sorted(set(note.related_clause_ids) & touched)
            if hit:
                note.status = "needs_review"
                note.review_reason = f"изменились пункты регламента: {', '.join(hit)}"
                flagged.append(note.id)
        return flagged

    # ---------- разъяснения ----------

    def add_note(
        self,
        *,
        question: str,
        answer: str,
        department_ids: list[str],
        related_clause_ids: list[str],
        keywords: list[str],
        expert: str,
        ticket_id: int | None,
    ) -> NoteRow:
        vec = self.embedder.embed([f"{question}\n{answer}\n{' '.join(keywords)}"])[0]
        with self.sessions.begin() as s:
            fingerprints = {
                c.id: c.fingerprint for c in s.scalars(select(ClauseRow).where(ClauseRow.id.in_(related_clause_ids)))
            }
            note = NoteRow(
                canonical_question=question,
                answer=answer,
                department_ids=department_ids,
                related_clause_ids=related_clause_ids,
                related_fingerprints=fingerprints,
                keywords=keywords,
                expert=expert,
                ticket_id=ticket_id,
                embedding=to_bytes(vec),
                status="published",
            )
            s.add(note)
            s.flush()
        self.rebuild_index()
        return note

    def set_note_status(self, note_id: int, status: str, reason: str = "") -> None:
        with self.sessions.begin() as s:
            note = s.get(NoteRow, note_id)
            if note is None:
                raise KeyError(note_id)
            note.status, note.review_reason = status, reason
        self.rebuild_index()

    # ---------- индекс ----------

    def rebuild_index(self) -> None:
        units: list[Unit] = []
        vectors: list[np.ndarray[Any, np.dtype[np.float32]]] = []
        with self.sessions() as s:
            titles = {d.id: d.title for d in s.scalars(select(DocumentRow))}
            for c in s.scalars(
                select(ClauseRow).where(ClauseRow.active.is_(True)).order_by(ClauseRow.doc_id, ClauseRow.ord)
            ):
                units.append(
                    Unit(
                        id=c.id,
                        kind="clause",
                        departments=(c.department,),
                        process=c.process,
                        title=clause_ref(c.number, titles.get(c.doc_id, c.doc_id)),
                        text=c.text,
                        search_text=f"{titles.get(c.doc_id, '')}. {' / '.join(c.path)}\n{c.number}. {c.text}",
                        parent=c.parent,
                        doc_id=c.doc_id,
                        number=c.number,
                    )
                )
                vectors.append(from_bytes(c.embedding) if c.embedding else self.embedder.embed([c.text])[0])
            for n in s.scalars(select(NoteRow).where(NoteRow.status == "published")):
                units.append(
                    Unit(
                        id=n.note_id,
                        kind="note",
                        departments=tuple(n.department_ids),
                        process=None,
                        title=f"Разъяснение службы качества от {n.created_at:%d.%m.%Y}",
                        text=n.answer,
                        search_text=f"{n.canonical_question}\n{n.answer}\n{' '.join(n.keywords)}",
                    )
                )
                vectors.append(from_bytes(n.embedding) if n.embedding else self.embedder.embed([n.answer])[0])
        matrix = np.vstack(vectors).astype(np.float32) if vectors else None
        self.index.rebuild(units, matrix)
        log.info("индекс пересобран: %d единиц", len(units))

    def missing_references(self, clause_ids: Iterable[str]) -> list[str]:
        """Внешние документы и несуществующие пункты, на которые ссылаются указанные пункты."""
        ids = list(clause_ids)
        if not ids:
            return []
        with self.sessions() as s:
            rows = s.scalars(select(ReferenceRow).where(ReferenceRow.clause_id.in_(ids)))
            out = []
            for r in rows:
                if r.kind == "document":
                    out.append(r.target)
                elif r.exists is False:
                    out.append(f"п. {r.target} (в документе такого пункта нет; ссылка из {r.clause_id.split(':')[1]})")
            return list(dict.fromkeys(out))
