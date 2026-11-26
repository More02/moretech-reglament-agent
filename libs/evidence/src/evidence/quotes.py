"""Поиск дословной цитаты в тексте пункта."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from ru_text import normalize

MIN_QUOTE_CHARS = 12
FUZZY_THRESHOLD = 92.0


@dataclass(frozen=True, slots=True)
class QuoteMatch:
    score: float
    exact: bool


def _clean(text: str) -> str:
    return normalize(text).replace('"', "").replace("•", " ").replace("  ", " ")


def find_quote(quote: str, text: str, *, threshold: float = FUZZY_THRESHOLD) -> QuoteMatch | None:
    """Цитата найдена в тексте - точно или с мелкими отличиями. Слишком короткая цитата не доказывает ничего."""
    q = _clean(quote).strip(" .,;:")
    t = _clean(text)
    if len(q) < MIN_QUOTE_CHARS:
        return None
    if q in t:
        return QuoteMatch(score=100.0, exact=True)
    alignment = fuzz.partial_ratio_alignment(q, t)
    if alignment is not None and alignment.score >= threshold:
        return QuoteMatch(score=float(alignment.score), exact=False)
    return None
