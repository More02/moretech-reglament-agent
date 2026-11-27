"""Почта: отправка по SMTP, чтение по IMAP; почтовый ящик в памяти - для тестов и локальной разработки."""

from __future__ import annotations

import re
import smtplib
import ssl
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OutgoingMail:
    to: list[str]
    cc: list[str]
    subject: str
    body: str
    in_reply_to: str = ""
    references: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class IncomingMail:
    message_id: str
    sender: str
    recipients: list[str]
    subject: str
    body: str
    in_reply_to: str = ""
    references: list[str] = field(default_factory=list)
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MailTransport(Protocol):
    address: str

    def send(self, mail: OutgoingMail) -> str:
        """Отправляет письмо и возвращает его Message-ID."""
        ...

    def fetch_new(self) -> list[IncomingMail]:
        """Новые входящие письма (каждое - один раз)."""
        ...


_QUOTE_STARTS = (
    re.compile(r"^-{2,}\s*(Original Message|Исходное сообщение|Пересылаемое сообщение)", re.IGNORECASE),
    re.compile(r"^(On .+ wrote:|.+ пишет:|.+ написал\(а\):)\s*$", re.IGNORECASE),
    re.compile(r"^(От|From):\s", re.IGNORECASE),
)


def strip_quoted(body: str) -> str:
    """Текст письма без цитирования предыдущих писем."""
    lines: list[str] = []
    for line in body.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if any(p.match(stripped) for p in _QUOTE_STARTS):
            break
        if stripped.startswith(">"):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def email_of(value: str) -> str:
    return parseaddr(value)[1].lower()


class MemoryMailbox:
    """Почтовый ящик в памяти. ``deliver`` имитирует входящее письмо."""

    def __init__(self, address: str = "agent@example.ru") -> None:
        self.address = address
        self.sent: list[tuple[str, OutgoingMail]] = []
        self._inbox: list[IncomingMail] = []

    def send(self, mail: OutgoingMail) -> str:
        msg_id = f"<{uuid.uuid4().hex}@reglament.local>"
        self.sent.append((msg_id, mail))
        return msg_id

    def deliver(self, mail: IncomingMail) -> None:
        self._inbox.append(mail)

    def fetch_new(self) -> list[IncomingMail]:
        out, self._inbox = self._inbox, []
        return out


class ImapSmtpMailbox:
    """Настоящий ящик агента: SMTP (SSL) для отправки, IMAP для чтения непрочитанных писем."""

    def __init__(
        self, *, smtp_host: str, smtp_port: int, imap_host: str, imap_port: int, user: str, password: str
    ) -> None:
        self.address = user
        self._smtp = (smtp_host, smtp_port)
        self._imap = (imap_host, imap_port)
        self._password = password

    def send(self, mail: OutgoingMail) -> str:
        msg = EmailMessage()
        msg["From"] = self.address
        msg["To"] = ", ".join(mail.to)
        if mail.cc:
            msg["Cc"] = ", ".join(mail.cc)
        msg["Subject"] = mail.subject
        msg_id = make_msgid(domain=self.address.split("@")[-1])
        msg["Message-ID"] = msg_id
        if mail.in_reply_to:
            msg["In-Reply-To"] = mail.in_reply_to
            msg["References"] = " ".join([*mail.references, mail.in_reply_to])
        msg.set_content(mail.body)
        with smtplib.SMTP_SSL(*self._smtp, context=ssl.create_default_context(), timeout=30) as smtp:
            smtp.login(self.address, self._password)
            smtp.send_message(msg, to_addrs=[*mail.to, *mail.cc])
        return msg_id

    def fetch_new(self) -> list[IncomingMail]:
        from imap_tools import AND, MailBox

        out: list[IncomingMail] = []
        with MailBox(self._imap[0], port=self._imap[1]).login(self.address, self._password) as box:
            for m in box.fetch(AND(seen=False), mark_seen=True, bulk=True):
                headers = {str(k).lower(): v for k, v in dict(m.headers).items()}
                out.append(
                    IncomingMail(
                        message_id=(headers.get("message-id") or (f"<{m.uid}@imap>",))[0].strip(),
                        sender=email_of(m.from_),
                        recipients=[email_of(a) for a in (*m.to, *m.cc)],
                        subject=m.subject,
                        body=strip_quoted(m.text or re.sub(r"<[^>]+>", " ", m.html or "")),
                        in_reply_to=(headers.get("in-reply-to") or ("",))[0].strip(),
                        references=" ".join(headers.get("references") or ()).split(),
                        received_at=m.date if m.date.tzinfo else m.date.replace(tzinfo=UTC),
                    )
                )
        return out
