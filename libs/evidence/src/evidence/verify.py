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
