"""Чтение абзацев из DOCX и HTML (Confluence storage/export) в порядке следования."""

from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True, slots=True)
class Para:
    """Абзац исходного документа."""

    text: str
    is_list_item: bool = False


def _para_text(p: etree._Element) -> str:
    parts: list[str] = []
    for node in p.iter():
        if node.tag == f"{_W}t" and node.text:
            parts.append(node.text)
        elif node.tag in (f"{_W}tab", f"{_W}br", f"{_W}cr"):
            parts.append(" ")
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def read_docx(path: str | Path) -> list[Para]:
    """Абзацы DOCX, включая содержимое таблиц (построчно), без пустых строк."""
    with zipfile.ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    body = root.find(f"{_W}body")
    if body is None:
        return []
    out: list[Para] = []
    for el in body:
        if el.tag == f"{_W}p":
            _append_para(out, el)
        elif el.tag == f"{_W}tbl":
            out.extend(_read_table(el))
    return out


def _read_table(tbl: etree._Element) -> list[Para]:
    """Таблица с шапкой читается по столбцам («Обязательно: …», «При наличии: …»), чтобы не терять,
    к какой колонке относится строка; таблица без шапки - построчно через « | »."""
    rows = [
        [" ".join(_para_text(p) for p in tc.iter(f"{_W}p")).strip() for tc in row.iter(f"{_W}tc")]
        for row in tbl.iter(f"{_W}tr")
    ]
    rows = [r for r in rows if any(r)]
    if not rows:
        return []
    header = rows[0]
    has_header = len(rows) > 1 and all(cell and len(cell) <= 60 for cell in header)
    if not has_header:
        return [Para(text=" | ".join(c for c in r if c), is_list_item=True) for r in rows]
    out: list[Para] = []
    for col, name in enumerate(header):
        out.append(Para(text=f"{name}:"))
        for r in rows[1:]:
            if col < len(r) and r[col]:
                out.append(Para(text=r[col].lstrip("-– ").strip(), is_list_item=True))
    return out


def _append_para(out: list[Para], p: etree._Element) -> None:
    text = _para_text(p)
    if not text:
        return
    num = p.find(f"{_W}pPr/{_W}numPr")
    out.append(Para(text=text, is_list_item=num is not None))


_BLOCK_TAGS = ("p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th")


def read_html(source: str) -> list[Para]:
    """Абзацы HTML-страницы (экспорт или storage format Confluence)."""
    tree = etree.HTML(source)
    if tree is None:
        return []
    out: list[Para] = []
    for el in tree.iter(*_BLOCK_TAGS):
        if any(anc.tag in _BLOCK_TAGS for anc in el.iterancestors()):
            continue  # вложенный блок уже вошёл в текст родителя
        text = re.sub(r"\s+", " ", html.unescape("".join(str(t) for t in el.itertext()))).strip()
        if text:
            out.append(Para(text=text, is_list_item=el.tag in ("li", "td", "th")))
    return out
