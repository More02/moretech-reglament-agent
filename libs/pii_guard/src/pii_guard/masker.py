"""Маскирование ПДн токенами и обратная подстановка."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import lru_cache

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("ТЕЛЕФОН", re.compile(r"(?<!\d)(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)")),
    ("СНИЛС", re.compile(r"(?<!\d)\d{3}-\d{3}-\d{3}[ -]\d{2}(?!\d)")),
    ("ИНН", re.compile(r"(?<!\d)\d{12}(?!\d)")),
)
# «Иванов И. И.», «Иванов И.И.», «И. И. Иванов»
_FIO_FALLBACK = re.compile(
    r"\b[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.|\b[А-ЯЁ]\.\s?[А-ЯЁ]\.\s?[А-ЯЁ][а-яё]+"
)


@dataclass
class MaskResult:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)

    def unmask(self, text: str) -> str:
        for token, value in sorted(self.mapping.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(token, value)
        return text


NameFinder = Callable[[str], Iterable[str]]


@lru_cache(maxsize=1)
def _natasha_finder() -> NameFinder | None:
    try:
        from natasha import Doc, MorphVocab, NewsEmbedding, NewsNERTagger, Segmenter
    except ImportError:
        return None
    segmenter, emb = Segmenter(), NewsEmbedding()
    tagger, _ = NewsNERTagger(emb), MorphVocab()

    def find(text: str) -> list[str]:
        doc = Doc(text)
        doc.segment(segmenter)
        doc.tag_ner(tagger)
        return [text[s.start : s.stop] for s in doc.spans if s.type == "PER"]

    return find


class PiiGuard:
    """Маскирует ПДн. ``name_finder`` можно подменить в тестах; по умолчанию - Natasha или шаблон ФИО."""

    def __init__(self, *, enabled: bool = True, name_finder: NameFinder | None = None) -> None:
        self.enabled = enabled
        self._name_finder = name_finder

    def _names(self, text: str) -> list[str]:
        finder = self._name_finder or _natasha_finder()
        found = list(finder(text)) if finder else []
        found += _FIO_FALLBACK.findall(text)
        return [n for n in dict.fromkeys(found) if len(n) > 2]

    def mask(self, text: str) -> MaskResult:
        result = MaskResult(text=text)
        if not self.enabled or not text:
            return result
        reverse: dict[str, str] = {}
        counters: dict[str, int] = {}

        def token_for(kind: str, value: str) -> str:
            if value not in reverse:
                counters[kind] = counters.get(kind, 0) + 1
                tok = f"[{kind}_{counters[kind]}]"
                reverse[value] = tok
                result.mapping[tok] = value
            return reverse[value]

        masked = text
        for kind, pattern in _PATTERNS:
            masked = pattern.sub(lambda m, k=kind: token_for(k, m.group(0)), masked)  # type: ignore[misc]
        for name in sorted(self._names(masked), key=len, reverse=True):
            if "[" in name:
                continue
            masked = masked.replace(name, token_for("ПЕРСОНА", name))
        result.text = masked
        return result
