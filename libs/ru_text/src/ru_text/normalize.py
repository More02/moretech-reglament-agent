"""Нормализация и токенизация русского текста."""

from __future__ import annotations

import re
from functools import lru_cache

_TOKEN_RE = re.compile(r"[a-zа-я0-9]+(?:[-][a-zа-я0-9]+)*", re.IGNORECASE)
_QUOTES = str.maketrans({"«": '"', "»": '"', "„": '"', "“": '"', "”": '"', "’": "'", "–": "-", "—": "-", " ": " "})

STOPWORDS: frozenset[str] = frozenset(
    (
        "а",
        "без",
        "более",
        "бы",
        "был",
        "была",
        "были",
        "было",
        "быть",
        "в",
        "вам",
        "вас",
        "весь",
        "во",
        "вот",
        "все",
        "всего",
        "всех",
        "вы",
        "где",
        "да",
        "даже",
        "для",
        "до",
        "его",
        "ее",
        "если",
        "есть",
        "еще",
        "же",
        "за",
        "здесь",
        "и",
        "из",
        "или",
        "им",
        "их",
        "к",
        "как",
        "ко",
        "когда",
        "кто",
        "ли",
        "либо",
        "мне",
        "может",
        "мы",
        "на",
        "над",
        "надо",
        "наш",
        "не",
        "него",
        "нее",
        "нет",
        "ни",
        "них",
        "но",
        "ну",
        "о",
        "об",
        "однако",
        "он",
        "она",
        "они",
        "оно",
        "от",
        "очень",
        "по",
        "под",
        "при",
        "с",
        "со",
        "так",
        "также",
        "такой",
        "там",
        "те",
        "тем",
        "то",
        "того",
        "тоже",
        "той",
        "только",
        "том",
        "ты",
        "у",
        "уже",
        "хотя",
        "чего",
        "чей",
        "чем",
        "что",
        "чтобы",
        "чье",
        "чья",
        "эта",
        "эти",
        "это",
        "я",
        "ли",
        "какой",
        "какая",
        "какие",
        "каков",
        "сколько",
        "можно",
        "нужно",
        "ли",
        "мой",
        "моя",
        "мои",
        "свой",
        "своя",
        "свои",
        "который",
        "которая",
        "которые",
    )
)


def normalize(text: str) -> str:
    """Регистр, ё → е, типографские кавычки и тире, лишние пробелы."""
    text = text.translate(_QUOTES).lower().replace("ё", "е")
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize(text))


@lru_cache(maxsize=1)
def _morph() -> object:
    import pymorphy3

    return pymorphy3.MorphAnalyzer()


@lru_cache(maxsize=200_000)
def lemma(word: str) -> str:
    if not re.search("[а-я]", word):
        return word
    parsed = _morph().parse(word)  # type: ignore[attr-defined]
    if not parsed:
        return word
    best = parsed[0]
    # Причастия и деепричастия → глагол: «инициирована» и «инициировать» должны совпадать в поиске
    if best.tag.POS in ("PRTF", "PRTS", "GRND"):
        infinitive = best.inflect({"INFN"})
        if infinitive is not None:
            return str(infinitive.word).replace("ё", "е")
    return str(best.normal_form).replace("ё", "е")


def lemmas(text: str, *, drop_stopwords: bool = True) -> list[str]:
    out: list[str] = []
    for tok in tokens(text):
        lem = lemma(tok)
        if drop_stopwords and (lem in STOPWORDS or tok in STOPWORDS):
            continue
        out.append(lem)
    return out
