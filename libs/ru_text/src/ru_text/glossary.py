"""Глоссарий: синонимы и сокращения → каноническое название из регламентов."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ru_text.normalize import lemmas


@dataclass(frozen=True, slots=True)
class Term:
    canonical: str
    aliases: tuple[str, ...]


class Glossary:
    """Находит в тексте сокращения и синонимы и возвращает канонические термины.

    Сокращения из заглавных букв («РП», «SS») ищутся с учётом регистра и границ слова, чтобы «ПА» не совпадало
    с «папка»; остальные синонимы - по леммам («проджект-менеджеру» → «проджект менеджер»).
    """

    def __init__(self, terms: Iterable[Term]) -> None:
        self.terms = tuple(terms)
        self._abbr: list[tuple[re.Pattern[str], Term]] = []
        self._phrases: list[tuple[tuple[str, ...], Term]] = []
        for term in self.terms:
            for alias in (*term.aliases, term.canonical):
                if _is_abbreviation(alias):
                    pattern = re.compile(rf"(?<![A-Za-zА-Яа-яЁё]){re.escape(alias)}(?![A-Za-zА-Яа-яЁё])")
                    self._abbr.append((pattern, term))
                else:
                    key = tuple(lemmas(alias, drop_stopwords=False))
                    if key:
                        self._phrases.append((key, term))

    def find(self, text: str) -> list[Term]:
        found: dict[str, Term] = {}
        for pattern, term in self._abbr:
            if pattern.search(text):
                found.setdefault(term.canonical, term)
        text_lemmas = lemmas(text, drop_stopwords=False)
        for key, term in self._phrases:
            if _contains(text_lemmas, key):
                found.setdefault(term.canonical, term)
        return list(found.values())

    def expand(self, text: str) -> str:
        """Текст запроса + канонические названия найденных терминов (для поиска по ключевым словам)."""
        text_lemmas = lemmas(text, drop_stopwords=False)
        extra = [
            t.canonical
            for t in self.find(text)
            if not _contains(text_lemmas, tuple(lemmas(t.canonical, drop_stopwords=False)))
        ]
        return text if not extra else f"{text} ({'; '.join(extra)})"


def _is_abbreviation(alias: str) -> bool:
    letters = [ch for ch in alias if ch.isalpha()]
    return bool(letters) and len(alias) <= 6 and all(ch.isupper() for ch in letters)


def _contains(haystack: list[str], needle: tuple[str, ...]) -> bool:
    n = len(needle)
    return any(tuple(haystack[i : i + n]) == needle for i in range(len(haystack) - n + 1))
