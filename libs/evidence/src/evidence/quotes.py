"""Поиск дословной цитаты в тексте пункта."""

from __future__ import annotations

import re
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


_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…|\[\.\.\.\]|\(\.\.\.\))\s*")
MIN_FRAGMENT_CHARS = 8


def find_quote(quote: str, text: str, *, threshold: float = FUZZY_THRESHOLD) -> QuoteMatch | None:
    """Цитата найдена в тексте - точно или с мелкими отличиями. Слишком короткая цитата не доказывает ничего.

    Цитата с пропуском («начало … конец») засчитывается, если каждый фрагмент найден в тексте и в том же порядке.
    """
    fragments = [f for f in (_clean(x).strip(" .,;:") for x in _ELLIPSIS.split(quote)) if f]
    t = _clean(text)
    if sum(len(f) for f in fragments) < MIN_QUOTE_CHARS:
        return None
    if len(fragments) > 1:
        return _find_fragments(fragments, t, threshold)
    return _find_one(fragments[0], t, threshold)


def _find_one(q: str, t: str, threshold: float) -> QuoteMatch | None:
    if q in t:
        return QuoteMatch(score=100.0, exact=True)
    alignment = fuzz.partial_ratio_alignment(q, t)
    if alignment is not None and alignment.score >= threshold:
        return QuoteMatch(score=float(alignment.score), exact=False)
    return None


def _find_fragments(fragments: list[str], t: str, threshold: float) -> QuoteMatch | None:
    position, scores, exact = 0, [], True
    for frag in fragments:
        if len(frag) < MIN_FRAGMENT_CHARS:
            return None
        rest = t[position:]
        idx = rest.find(frag)
        if idx >= 0:
            position += idx + len(frag)
            scores.append(100.0)
            continue
        alignment = fuzz.partial_ratio_alignment(frag, rest)
        if alignment is None or alignment.score < threshold:
            return None
        position += alignment.dest_end
        scores.append(float(alignment.score))
        exact = False
    return QuoteMatch(score=min(scores), exact=exact)
