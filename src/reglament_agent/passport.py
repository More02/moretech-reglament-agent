"""Паспорт компании: всё, что отличает одну компанию от другой."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ru_text import Glossary, Term


class Department(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    full_name: str
    aliases: list[str] = Field(default_factory=list)


class ProcessDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class DocumentDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file: str
    id: str
    title: str
    department: str
    processes: list[str]
    sections: dict[str, str] = Field(default_factory=dict, description="процесс → диапазон разделов «1-6»")
    confluence_page_id: str | None = None

    def process_of(self, clause_number: str) -> str | None:
        """Стадия пункта по номеру раздела; если документ про одну стадию - она."""
        if len(self.processes) == 1:
            return self.processes[0]
        top = int(clause_number.split(".")[0]) if clause_number[0].isdigit() else 0
        for process, span in self.sections.items():
            lo, _, hi = span.partition("-")
            if int(lo) <= top <= int(hi or lo):
                return process
        return None


class GlossaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical: str
    aliases: list[str]


class OutOfScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str
    examples: list[str] = Field(default_factory=list)
    redirect: str


class QualityService(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    email_env: str
    authorized_senders_env: str


class DialogRules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_clarifications: int = 2
    auto_send_escalation: bool = False


class DemoProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    email: str
    position: str = ""
    department: str | None = None


class Passport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    company: str
    assistant_name: str
    quality_service: QualityService
    dialog: DialogRules = DialogRules()
    departments: list[Department]
    processes: list[ProcessDef]
    documents: list[DocumentDef]
    glossary: list[GlossaryEntry]
    out_of_scope: list[OutOfScope] = Field(default_factory=list)
    off_task_examples: list[str] = Field(default_factory=list)
    demo_profiles: list[DemoProfile] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> Passport:
        with path.open(encoding="utf-8") as fh:
            return cls.model_validate(yaml.safe_load(fh))

    def department(self, dep_id: str) -> Department:
        return next(d for d in self.departments if d.id == dep_id)

    def document(self, doc_id: str) -> DocumentDef:
        return next(d for d in self.documents if d.id == doc_id)

    def build_glossary(self) -> Glossary:
        return Glossary(Term(g.canonical, tuple(g.aliases)) for g in self.glossary)
