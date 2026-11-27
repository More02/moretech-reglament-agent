"""Аналитика для службы качества: что спрашивают, где регламенты молчат, что пора актуализировать, сколько стоит."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from reglament_agent.adapters.db import ClauseRow, DocumentRow, NoteRow, TicketRow, TurnRow
from reglament_agent.passport import Passport

UNANSWERED = {"not_found", "conflict", "escalation_sent"}


class Analytics:
    def __init__(self, sessions: sessionmaker[Session], passport: Passport) -> None:
        self.sessions = sessions
        self.passport = passport

    def summary(self, days: int = 30) -> dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=days)
        with self.sessions() as s:
            turns = list(s.scalars(select(TurnRow).where(TurnRow.created_at >= since).order_by(TurnRow.id)))
            agent = [t for t in turns if t.role == "agent" and t.outcome and t.outcome != "quality_reply"]
            tickets = list(s.scalars(select(TicketRow)))
            notes = list(s.scalars(select(NoteRow)))
            clauses = {c.id: c for c in s.scalars(select(ClauseRow))}
            titles = {d.id: d.title for d in s.scalars(select(DocumentRow))}
            questions = self._questions(turns)
        outcomes = Counter(t.outcome for t in agent)
        answered = [t for t in agent if t.outcome == "answer"]
        rated = [t.rating for t in agent if t.rating is not None]
        return {
            "period_days": days,
            "totals": {
                "questions": len(agent),
                "answered": outcomes.get("answer", 0),
                "clarified": outcomes.get("clarify", 0),
                "not_found": sum(outcomes.get(k, 0) for k in UNANSWERED),
                "out_of_scope": outcomes.get("out_of_scope", 0) + outcomes.get("off_task", 0),
                "answer_rate": round(outcomes.get("answer", 0) / len(agent), 3) if agent else 0.0,
                "avg_latency_ms": int(sum(t.latency_ms for t in answered) / len(answered)) if answered else 0,
                "avg_cost_rub": round(sum(t.cost_rub for t in agent) / len(agent), 4) if agent else 0.0,
                "total_cost_rub": round(sum(t.cost_rub for t in agent), 2),
                "rating_positive_share": round(sum(1 for r in rated if r > 0) / len(rated), 3) if rated else None,
            },
            "outcomes": dict(outcomes),
            "by_department": self._by_department(agent),
            "coverage": self._coverage(agent, clauses, titles),
            "unanswered": [q for q in questions if q["outcome"] in UNANSWERED][-50:],
            "tickets": {
                "open": sum(1 for t in tickets if t.status == "sent"),
                "answered": sum(1 for t in tickets if t.status == "answered"),
                "avg_hours_to_answer": self._avg_hours(tickets),
                "items": [
                    {
                        "code": t.code,
                        "question": t.question,
                        "status": t.status,
                        "employee": t.employee_name,
                        "created_at": t.created_at.isoformat(),
                        "note_id": t.note_id,
                    }
                    for t in sorted(tickets, key=lambda t: t.id, reverse=True)[:50]
                ],
            },
            "notes": {
                "published": sum(1 for n in notes if n.status == "published"),
                "needs_review": [
                    {"id": n.id, "question": n.canonical_question, "reason": n.review_reason}
                    for n in notes
                    if n.status == "needs_review"
                ],
            },
            "actualization_candidates": self._candidates(agent, clauses, titles, notes),
        }

    @staticmethod
    def _questions(turns: list[TurnRow]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        last_q: dict[str, TurnRow] = {}
        for t in turns:
            if t.role == "employee":
                last_q[t.conversation_id] = t
            elif t.outcome and t.conversation_id in last_q:
                q = last_q[t.conversation_id]
                out.append(
                    {"text": q.text, "outcome": t.outcome, "at": t.created_at.isoformat(), "departments": t.departments}
                )
        return out

    def _by_department(self, agent: list[TurnRow]) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter(d for t in agent for d in set(t.departments))
        return [{"id": d.id, "name": d.name, "answers": counts.get(d.id, 0)} for d in self.passport.departments]

    @staticmethod
    def _section_key(clause: ClauseRow) -> str:
        return f"{clause.doc_id}:{clause.number.split('.')[0]}"

    def _coverage(
        self, agent: list[TurnRow], clauses: dict[str, ClauseRow], titles: dict[str, str]
    ) -> list[dict[str, Any]]:
        cited: Counter[str] = Counter()
        for t in agent:
            for cid in set(t.clause_ids):
                if cid in clauses:
                    cited[self._section_key(clauses[cid])] += 1
        sections: dict[str, str] = {}
        for c in clauses.values():
            if c.active and "." not in c.number and c.number != "0":
                sections[f"{c.doc_id}:{c.number}"] = f"{c.number}. {c.heading}"
        rows = [
            {"document": titles.get(key.split(":")[0], ""), "section": name, "citations": cited.get(key, 0)}
            for key, name in sections.items()
        ]
        return sorted(rows, key=lambda r: -int(r["citations"]))

    @staticmethod
    def _avg_hours(tickets: list[TicketRow]) -> float | None:
        spans = [(t.answered_at - t.sent_at).total_seconds() / 3600 for t in tickets if t.answered_at and t.sent_at]
        return round(sum(spans) / len(spans), 2) if spans else None

    def _candidates(
        self, agent: list[TurnRow], clauses: dict[str, ClauseRow], titles: dict[str, str], notes: list[NoteRow]
    ) -> list[dict[str, Any]]:
        """Разделы, где регламент чаще всего «не дотягивает»: уточнения, отсутствие ответа, разъяснения поверх."""
        score: defaultdict[str, Counter[str]] = defaultdict(Counter)
        for t in agent:
            if t.outcome in ("clarify", "not_found", "conflict"):
                for cid in set(t.clause_ids) or set():
                    if cid in clauses:
                        score[self._section_key(clauses[cid])][t.outcome] += 1
        for n in notes:
            for cid in n.related_clause_ids:
                if cid in clauses:
                    score[self._section_key(clauses[cid])]["notes"] += 1
        rows: list[dict[str, Any]] = []
        for key, c in score.items():
            doc_id, number = key.split(":")
            head = clauses.get(f"{doc_id}:{number}")
            rows.append(
                {
                    "document": titles.get(doc_id, doc_id),
                    "section": f"{number}. {head.heading if head else ''}",
                    "signals": dict(c),
                    "weight": sum(c.values()),
                }
            )
        return sorted(rows, key=lambda r: -int(r["weight"]))[:20]
