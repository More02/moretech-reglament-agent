"""Ссылки из текста пункта: на пункты этого документа и на другие документы."""

from __future__ import annotations

import re

from reg_parse.model import Clause, DocReference

_CLAUSE_REF = re.compile(r"(?:п\.|пункт[а-я]*)\s*(\d{1,3}(?:\.\d{1,3}){0,4})", re.IGNORECASE)
# «регламента подбора субподрядчика», «Инструкции по работе с системой управления проектами»,
# «процедуры контроля маржинальности сделок»; останавливаемся на знаке препинания или скобке.
_DOC_REF = re.compile(
    r"(?P<kind>регламент[а-я]*|инструкци[а-я]*|процедур[а-я]*(?=\s+контроля))\s+(?P<name>[а-яё][а-яё\s\-]{6,80}?)(?=[.,;:)(]|$)",
    re.IGNORECASE,
)
# Слова, после которых это не название документа, а обычная речь
_NOT_A_NAME = (
    "по проектной",
    "по проектам",
    "в целом",
    "данного",
    "этого",
    "который",
    "которые",
    "под ",
    "по созданию",
)


def _normalize_doc_name(kind: str, name: str) -> str:
    base = kind.lower()
    stem = "регламент" if base.startswith("регламент") else "инструкция" if base.startswith("инструкц") else "процедура"
    return f"{stem} {name.strip().lower()}"


def find_references(clause: Clause, known_numbers: set[str]) -> list[DocReference]:
    refs: list[DocReference] = []
    seen: set[tuple[str, str]] = set()
    for m in _CLAUSE_REF.finditer(clause.text):
        target = m.group(1).rstrip(".")
        key = ("clause", target)
        if key in seen:
            continue
        seen.add(key)
        exists = target in known_numbers
        refs.append(DocReference(clause_id=clause.clause_id, kind="clause", target=target, exists=exists))
    for m in _DOC_REF.finditer(clause.text):
        name = m.group("name")
        if any(name.lower().startswith(stop) for stop in _NOT_A_NAME) or len(name.split()) < 2:
            continue
        target = _normalize_doc_name(m.group("kind"), name)
        key = ("document", target)
        if key in seen:
            continue
        seen.add(key)
        refs.append(DocReference(clause_id=clause.clause_id, kind="document", target=target))
    return refs
