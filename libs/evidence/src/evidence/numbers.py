"""Числа в тексте: цифрами и словами («три рабочих дня», «двух недель»)."""

from __future__ import annotations

import re

from ru_text import normalize

# Основы числительных: «две», «двух», «двум» → 2. Порядок важен: длинные основы раньше коротких.
_WORD_STEMS: tuple[tuple[str, int], ...] = (
    ("двенадцат", 12),
    ("одиннадцат", 11),
    ("десят", 10),
    ("девят", 9),
    ("восьм", 8),
    ("восем", 8),
    ("сем", 7),
    ("шест", 6),
    ("пят", 5),
    ("четыр", 4),
    ("четвер", 4),
    ("тр", 3),
    ("дв", 2),
    ("одн", 1),
    ("один", 1),
)
_WORDS = {
    "один", "одна", "одного", "одной", "одну", "одним", "два", "две", "двух", "двум", "двумя", "три", "трех", "трем",
    "тремя", "четыре", "четырех", "четырем", "пять", "пяти", "шесть", "шести", "семь", "семи", "восемь", "восьми",
    "девять", "девяти", "десять", "десяти", "одиннадцать", "одиннадцати", "двенадцать", "двенадцати",
}  # fmt: skip
_DIGITS = re.compile(r"(?<![\d.])(\d+(?:[.,]\d+)?)(?![\d.]*\d)")
_WORD_RE = re.compile(r"[а-я]+")


def _word_value(word: str) -> int | None:
    if word not in _WORDS:
        return None
    return next((value for stem, value in _WORD_STEMS if word.startswith(stem)), None)


def numbers(text: str) -> set[str]:
    """Множество чисел в тексте в виде строк ('3', '12', '0.5'). Номера пунктов («п. 8.4») не считаются."""
    norm = normalize(text)
    norm = re.sub(r"(?:п\.|пункт[а-я]*|раздел[а-я]*)\s*\d+(?:\.\d+)*", " ", norm)
    found = {m.group(1).replace(",", ".") for m in _DIGITS.finditer(norm)}
    for w in _WORD_RE.findall(norm):
        value = _word_value(w)
        if value is not None:
            found.add(str(value))
    return found
