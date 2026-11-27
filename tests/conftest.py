"""Синтетический корпус из двух подразделений и сборка приложения на тестовой модели и ящике в памяти."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import docx
import pytest
import yaml

from reglament_agent.adapters.mail import MemoryMailbox
from reglament_agent.config import Settings
from reglament_agent.container import Container, build_container

DOCS = {
    "alpha.docx": [
        "Проектная деятельность Альфа",
        "1. Пресейл",
        "1.1. Заявка на пресейл должна быть инициирована не менее чем за 3 рабочих дня до подачи предложения Заказчику.",
        "1.2. Бюджетная оценка не может использоваться для подачи в конкурс (за исключением RFI).",
        "2. Реализация",
        "2.1. Руководитель проекта обновляет реестр рисков не реже 1 раза в неделю.",
        "2.2. Работы без подписанного договора запрещены. Порядок подбора - по регламенту подбора субподрядчика.",
    ],
    "beta.docx": [
        "Проектная деятельность Бета",
        "1. Пресейл",
        "1.1. Расчёт должен быть инициирован за 2 недели до подачи конкурса.",
        "2. Реализация",
        "2.1. Руководитель проекта обновляет реестр рисков не реже 1 раза в месяц.",
    ],
}

PASSPORT = {
    "id": "test",
    "company": "Тест",
    "assistant_name": "Агент по регламентам",
    "quality_service": {"name": "Служба качества", "email_env": "QUALITY_EMAIL", "authorized_senders_env": "X"},
    "dialog": {"max_clarifications": 2, "auto_send_escalation": False},
    "departments": [
        {"id": "alpha", "name": "Альфа", "full_name": "Дирекция Альфа", "aliases": ["Альфа"]},
        {"id": "beta", "name": "Бета", "full_name": "Дирекция Бета", "aliases": ["Бета"]},
    ],
    "processes": [
        {"id": "presale", "name": "Пресейл", "aliases": []},
        {"id": "project", "name": "Проект", "aliases": []},
    ],
    "documents": [
        {
            "file": "alpha.docx",
            "id": "alpha-doc",
            "title": "Проектная деятельность Альфа",
            "department": "alpha",
            "processes": ["presale", "project"],
            "sections": {"presale": "1-1", "project": "2-99"},
        },
        {
            "file": "beta.docx",
            "id": "beta-doc",
            "title": "Проектная деятельность Бета",
            "department": "beta",
            "processes": ["presale", "project"],
            "sections": {"presale": "1-1", "project": "2-99"},
        },
    ],
    "glossary": [{"canonical": "Руководитель проекта", "aliases": ["РП", "PM", "проджект"]}],
    "out_of_scope": [{"topic": "Премия", "examples": [], "redirect": "Обратитесь к своему руководителю."}],
    "off_task_examples": [],
}


@pytest.fixture
def app(tmp_path: Path) -> Iterator[tuple[Container, MemoryMailbox]]:
    regs = tmp_path / "regs"
    regs.mkdir()
    for name, lines in DOCS.items():
        d = docx.Document()
        for line in lines:
            d.add_paragraph(line)
        d.save(str(regs / name))
    passport = tmp_path / "passport.yaml"
    passport.write_text(yaml.safe_dump(PASSPORT, allow_unicode=True), encoding="utf-8")
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        llm_fake=True,
        embeddings_backend="hashing",
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        passport_path=passport,
        regulations_dir=regs,
        quality_email="quality@corp.test",
    )
    mailbox = MemoryMailbox("agent@corp.test")
    container = build_container(settings, mail_transport=mailbox)
    container.kb.ingest(container.kb.parse_directory(regs))
    yield container, mailbox
