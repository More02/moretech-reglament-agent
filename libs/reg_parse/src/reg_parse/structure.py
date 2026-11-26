"""Построение дерева пунктов из последовательности абзацев."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from reg_parse.model import Clause, ParsedDocument
from reg_parse.readers import Para
from reg_parse.refs import find_references

# «8.», «8.4.», «8.4.1.», «20.2.1» в начале абзаца; номер раздела верхнего уровня обязан заканчиваться точкой,
# иначе «3 рабочих дня» в начале строки сочли бы пунктом.
_NUMBER_RE = re.compile(r"^(?P<num>\d{1,3}(?:\.\d{1,3}){0,4})(?P<dot>\.)?\s+(?P<rest>\S.*)$")
_INTRO = "0"


@dataclass
class _Draft:
    number: str
    heading: str
    lines: list[str] = field(default_factory=list)


def _match_number(text: str) -> tuple[str, str] | None:
    m = _NUMBER_RE.match(text)
    if not m:
        return None
    num = m.group("num")
    if "." not in num and not m.group("dot"):
        return None
    return num, m.group("rest").strip()


def _parent_of(number: str, known: set[str]) -> str | None:
    parts = number.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:cut])
        if candidate in known:
            return candidate
    return None


def _is_plausible_next(number: str, seen: list[str]) -> bool:
    """Отсекает перечисления вида «• 20.2.1. Сроки» внутри пункта 20.2 - они остаются частью родителя,
    но настоящий следующий пункт (8.5 после 8.4) или подпункт (8.4.1) - принимаем."""
    if not seen:
        return True
    return number not in seen


def build_document(doc_id: str, paragraphs: Sequence[Para], title: str | None = None) -> ParsedDocument:
    """Собирает пункты. Абзацы без номера (перечисления, «Важно:», пояснения) относятся к текущему пункту."""
    paras = list(paragraphs)
    if title is None and paras:
        title = paras.pop(0).text
    title = title or doc_id

    drafts: list[_Draft] = []
    seen: list[str] = []
    for para in paras:
        matched = _match_number(para.text)
        if matched and _is_plausible_next(matched[0], seen):
            number, rest = matched
            drafts.append(_Draft(number=number, heading=rest))
            seen.append(number)
            continue
        line = f"• {para.text}" if para.is_list_item else para.text
        if not drafts:
            drafts.append(_Draft(number=_INTRO, heading=para.text))
            seen.append(_INTRO)
            continue
        drafts[-1].lines.append(line)

    return _finalize(doc_id, title, drafts)


def _finalize(doc_id: str, title: str, drafts: list[_Draft]) -> ParsedDocument:
    known: set[str] = set()
    headings: dict[str, str] = {}
    clauses: list[Clause] = []
    for order, d in enumerate(drafts):
        parent = _parent_of(d.number, known) if d.number != _INTRO else None
        path: list[str] = []
        cursor = parent
        while cursor is not None:
            path.insert(0, f"{cursor}. {headings[cursor]}")
            cursor = _parent_of(cursor, known)
        text = "\n".join([d.heading, *d.lines]).strip()
        clauses.append(
            Clause(
                doc_id=doc_id,
                number=d.number,
                heading=d.heading,
                text=text,
                parent=parent,
                path=tuple(path),
                order=order,
            )
        )
        known.add(d.number)
        headings[d.number] = d.heading
    refs = tuple(r for c in clauses for r in find_references(c, known))
    return ParsedDocument(doc_id=doc_id, title=title, clauses=tuple(clauses), references=refs)
