"""Схема базы данных (SQLAlchemy 2.0). Работает на PostgreSQL в эксплуатации и на SQLite в тестах."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[str]: JSON}  # noqa: RUF012 - конфигурация SQLAlchemy


class DocumentRow(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    department: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(500))
    fingerprint: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ClauseRow(Base):
    __tablename__ = "clauses"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    number: Mapped[str] = mapped_column(String(32))
    heading: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    path: Mapped[list[str]] = mapped_column(JSON, default=list)
    parent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ord: Mapped[int] = mapped_column(Integer)
    department: Mapped[str] = mapped_column(String(64), index=True)
    process: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(32))
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReferenceRow(Base):
    __tablename__ = "references"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clause_id: Mapped[str] = mapped_column(String(100), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    target: Mapped[str] = mapped_column(String(300))
    exists: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class NoteRow(Base):
    """Разъяснение службы качества."""

    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    department_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_clause_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_fingerprints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    expert: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    review_reason: Mapped[str] = mapped_column(Text, default="")
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @property
    def note_id(self) -> str:
        return f"note:{self.id}"


class TicketRow(Base):
    """Обращение в службу качества."""

    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    employee_name: Mapped[str] = mapped_column(String(300))
    employee_email: Mapped[str] = mapped_column(String(300))
    department: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default="")
    candidate_clause_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    message_id: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def code(self) -> str:
        return f"РЕГ-{self.id:04d}"


class MailRow(Base):
    __tablename__ = "mail_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(8))
    message_id: Mapped[str] = mapped_column(String(300), unique=True)
    in_reply_to: Mapped[str] = mapped_column(String(300), default="")
    sender: Mapped[str] = mapped_column(String(300))
    recipients: Mapped[list[str]] = mapped_column(JSON, default=list)
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(32), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConversationRow(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    channel_key: Mapped[str | None] = mapped_column(String(250), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TurnRow(Base):
    __tablename__ = "turns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    outcome: Mapped[str] = mapped_column(String(32), default="", index=True)
    departments: Mapped[list[str]] = mapped_column(JSON, default=list)
    clause_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_rub: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class LlmCallRow(Base):
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost_rub: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Any]:
    return sessionmaker(engine, expire_on_commit=False)
