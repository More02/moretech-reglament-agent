"""Проверка утверждения ответа: цитата есть в пункте, числа утверждения есть в цитате."""

from __future__ import annotations

from dataclasses import dataclass, field

from evidence.numbers import numbers
from evidence.quotes import QuoteMatch, find_quote


@dataclass(frozen=True, slots=True)
class ClaimCheck:
    ok: bool
    quote_match: QuoteMatch | None
    unsupported_numbers: frozenset[str] = field(default_factory=frozenset)
    reason: str = ""


def verify_claim(claim: str, quote: str, clause_text: str) -> ClaimCheck:
    match = find_quote(quote, clause_text)
    if match is None:
        return ClaimCheck(ok=False, quote_match=None, reason="цитата не найдена в тексте пункта")
    missing = frozenset(numbers(claim) - numbers(quote))
    if missing:
        return ClaimCheck(
            ok=False,
            quote_match=match,
            unsupported_numbers=missing,
            reason=f"в цитате нет чисел из утверждения: {', '.join(sorted(missing))}",
        )
    return ClaimCheck(ok=True, quote_match=match)


# Слова, меняющие смысл правила при прочих равных: единицы срока и модальность («можно» / «нельзя»)
CRITICAL_LEMMAS = frozenset(
    {
        "минута", "час", "день", "неделя", "месяц", "квартал", "год", "рабочий", "календарный",
        "можно", "нельзя", "запрещать", "запрещаться", "запрещено", "разрешать", "допускаться", "обязательно",
        "обязанный", "должный", "не", "исключение", "кроме", "только",
    }
)  # fmt: skip


def texts_differ(a: str, b: str, *, min_overlap: float = 0.45) -> bool:
    """Тексты расходятся по сути: разные числа, единицы срока или модальность, либо мало общих слов.
    Перефразирование одного и того же правила расхождением не считается."""
    from ru_text import lemmas

    if numbers(a) != numbers(b):
        return True
    full_a, full_b = set(lemmas(a, drop_stopwords=False)), set(lemmas(b, drop_stopwords=False))
    if (full_a & CRITICAL_LEMMAS) != (full_b & CRITICAL_LEMMAS):
        return True
    la, lb = set(lemmas(a)), set(lemmas(b))
    if not la or not lb:
        return False
    return len(la & lb) / len(la | lb) < min_overlap
