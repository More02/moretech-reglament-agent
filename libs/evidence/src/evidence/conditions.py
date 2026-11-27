"""Потерянное условие: цитата обрывает предложение-правило перед вторым условием или исключением.

«РП может привлечь субподрядчика только после подписания договора» - цитата верная, но в регламенте дальше
«и при наличии Заказа покупателя…». Утверждение по такой цитате формально подтверждено, а по смыслу неполно.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from evidence.quotes import _ELLIPSIS, _clean
from ru_text import lemmas

_RESTRICTIVE = re.compile(
    r"\b(только|запрещ\w*|не допуска\w*|не мо(?:гут|жет)\w*|не вправе|обязательн\w*|исключени\w*|кроме|необходимо)\b"
)
_CONTINUATION = re.compile(
    r"^(?:,\s*)?(?:и|а также|при (?:наличии|условии)|если|кроме|за исключением|после|в случае)\b"
)
_CONDITION_INSIDE = re.compile(r"(?:^|\s)(?:и при|при наличии|при условии|а также|за исключением|кроме)\b")
_EXCEPTION_SENTENCE = re.compile(r"^(?:исключени\w*|обязательным условием|кроме того,? исключ)")
_SENTENCE_END = re.compile(r"[.;!?](?:\s|$)|\n")
MIN_REST_CHARS = 8
COVERED_SCORE = 85.0


def _sentence_bounds(t: str, start: int, end: int) -> tuple[int, int]:
    head = max(t.rfind(". ", 0, start), t.rfind("\n", 0, start), t.rfind("; ", 0, start))
    tail = _SENTENCE_END.search(t, end)
    return head + 1 if head >= 0 else 0, tail.start() if tail else len(t)


def _locate(quote: str, t: str) -> tuple[int, int] | None:
    fragments = [f for f in (_clean(x).strip(" .,;:") for x in _ELLIPSIS.split(quote)) if f]
    if not fragments:
        return None
    first, last = fragments[0], fragments[-1]
    start = t.find(first)
    if start < 0:
        al = fuzz.partial_ratio_alignment(first, t)
        if al is None or al.score < COVERED_SCORE:
            return None
        start = al.dest_start
    idx = t.find(last, start)
    if idx >= 0:
        return start, idx + len(last)
    al = fuzz.partial_ratio_alignment(last, t[start:])
    if al is None or al.score < COVERED_SCORE:
        return None
    return start, start + al.dest_end


def _covered(rest: str, others: list[str]) -> bool:
    return any(fuzz.partial_ratio(rest[:80], _clean(o)) >= COVERED_SCORE for o in others)


def lost_condition(quote: str, text: str, other_quotes: list[str] | None = None) -> str | None:
    """Возвращает пропущенное продолжение правила (второе условие, исключение) или None.

    Продолжение не считается потерянным, если его цитирует другое утверждение того же ответа.
    """
    others = other_quotes or []
    t = _clean(text)
    span = _locate(quote, t)
    if span is None:
        return None
    s_start, s_end = _sentence_bounds(t, *span)
    sentence = t[s_start:s_end]
    rest = t[span[1] : s_end].strip()
    if (
        len(rest.strip(" ,.;")) >= MIN_REST_CHARS
        and (_CONTINUATION.match(rest) or _CONDITION_INSIDE.search(rest))
        and _RESTRICTIVE.search(sentence)
        and not _covered(rest, others)
    ):
        return rest.strip(" ,.;")
    following = t[s_end:].lstrip(" .;\n")
    nxt_end = _SENTENCE_END.search(following)
    nxt = following[: nxt_end.start() if nxt_end else len(following)].strip()
    if _RESTRICTIVE.search(sentence) and _EXCEPTION_SENTENCE.match(nxt) and not _covered(nxt, others):
        return nxt
    return None


def full_sentence(quote: str, text: str) -> str:
    """Предложение источника (в исходном написании), в котором стоит цитата, вместе с исключением после него."""
    sentences = [s.strip() for s in re.split(r"(?<=[.;!?])\s+|\n+", text) if s.strip()]
    if not sentences:
        return quote
    head = _ELLIPSIS.split(quote)[0]
    best = max(range(len(sentences)), key=lambda i: fuzz.partial_ratio(_clean(head), _clean(sentences[i])))
    picked = sentences[best]
    if best + 1 < len(sentences) and _EXCEPTION_SENTENCE.match(_clean(sentences[best + 1])):
        picked = f"{picked} {sentences[best + 1]}"
    return picked


_TEXT_CONDITION = re.compile(r"(?:\s|^)(?:и при|при наличии|при условии|за исключением|кроме|исключени\w*)\b")
MIN_COVERAGE = 0.34


def dropped_condition(claim: str, quote: str) -> str | None:
    """Цитата содержит второе условие или исключение правила, а утверждение его потеряло.

    «РП может привлечь субподрядчика только после подписания договора» при цитате «…только после подписания
    договора и при наличии Заказа покупателя…» - смысл правила искажён, хотя цитата верна.
    """
    q = _clean(quote)
    if not _RESTRICTIVE.search(q):
        return None
    m = _TEXT_CONDITION.search(q)
    if m is None:
        return None
    tail = q[m.start() :].strip(" ,.;")
    tail_lemmas = {w for w in lemmas(tail) if len(w) > 3}
    if len(tail_lemmas) < 2:
        return None
    claim_lemmas = set(lemmas(claim))
    if len(tail_lemmas & claim_lemmas) / len(tail_lemmas) >= MIN_COVERAGE:
        return None
    return tail


def foreign_line(claim: str, quote: str, text: str) -> bool:
    """Цитата взята из другой строки перечня, чем то, о чём утверждение.

    Пункт: «Отчётность включает: • исполнителей - раз в неделю; … • реестр рисков - раз в месяц». Утверждение
    «реестр рисков - раз в неделю» с цитатой «не реже одного раза в неделю» формально подтверждено, но срок
    взят из чужой строки. Предмет утверждения (слова вне цитаты) должен встречаться в строке цитаты или в
    заголовке перечня.
    """
    lines = [_clean(x) for x in re.split(r"\n|•", text) if x.strip()]
    if len(lines) < 3:
        return False
    fragments = [f for f in (_clean(x).strip(" .,;:") for x in _ELLIPSIS.split(quote)) if f]
    homes = [i for i, line in enumerate(lines) if all(f in line for f in fragments)]
    if not homes or 0 in homes:
        return False
    # Цитата - большая часть строки: предмет утверждения взят из неё же.
    quoted = sum(len(f) for f in fragments)
    if any(quoted >= 0.5 * len(lines[i]) for i in homes):
        return False
    from evidence.verify import TIME_WORDS

    def stems(t: str) -> set[str]:
        return {w[:5] for w in lemmas(t) if len(w) > 3 and w not in TIME_WORDS}

    subject = stems(claim) - stems(quote)
    if not subject:
        return False
    header = stems(lines[0])
    return all(not (subject & (stems(lines[i]) | header)) for i in homes)
