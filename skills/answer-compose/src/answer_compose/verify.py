"""Проверка ответа кодом: источник, цитата, числа, статусы, одинаковость вариантов."""

from __future__ import annotations

import re

from answer_compose.models import (
    Claim,
    ComposeInput,
    Composition,
    Conflict,
    RejectedClaim,
    Status,
    Variant,
    VerifiedComposition,
)
from evidence import dropped_condition, full_sentence, lost_condition, numbers, texts_differ, verify_claim
from ru_text import lemmas


def _allowed_sources(inp: ComposeInput) -> dict[str, dict[str, str]]:
    """department_id → {source_id: text}. Разъяснения доступны подразделениям из department_ids (пусто - всем)."""
    out: dict[str, dict[str, str]] = {}
    for dep in inp.departments:
        texts = {s.id: s.text for s in dep.sources}
        for note in inp.expert_notes:
            if not note.department_ids or dep.id in note.department_ids:
                texts[note.id] = f"{note.question}\n{note.answer}"
        out[dep.id] = texts
    return out


def _check_claim(dep_id: str, claim: Claim, allowed: dict[str, str]) -> RejectedClaim | None:
    if claim.source_id not in allowed:
        return RejectedClaim(department_id=dep_id, claim=claim, reason="источник не из найденных для подразделения")
    check = verify_claim(claim.text, claim.quote, allowed[claim.source_id])
    if not check.ok:
        return RejectedClaim(department_id=dep_id, claim=claim, reason=check.reason)
    return None


def _lead_supported(lead: str, claims: list[Claim]) -> bool:
    supported = set().union(*(numbers(c.quote) for c in claims)) if claims else set()
    return numbers(lead) <= supported


def verify_composition(raw: Composition, inp: ComposeInput) -> VerifiedComposition:
    allowed = _allowed_sources(inp)
    rejected: list[RejectedClaim] = []
    by_dep = {v.department_id: v for v in raw.variants if v.department_id in allowed}
    variants: list[Variant] = []
    for dep in inp.departments:
        variant = by_dep.get(dep.id) or Variant(department_id=dep.id, status=Status.NOT_FOUND)
        kept: list[Claim] = []
        for claim in variant.claims:
            problem = _check_claim(dep.id, claim, allowed[dep.id])
            if problem:
                rejected.append(problem)
            else:
                kept.append(claim)
        variants.append(
            _uncovered_parts(_restatus(variant, kept, dropped=len(variant.claims) - len(kept)), inp.question)
        )
    answered = [v for v in variants if v.status is not Status.NOT_FOUND]
    same = raw.same_across_departments and _same_facts(answered)
    conflict = _valid_conflict(raw.conflict, allowed)
    return VerifiedComposition(
        variants=variants,
        same_across_departments=same,
        conflict=conflict,
        missing_documents=list(dict.fromkeys(m.strip() for m in raw.missing_documents if m.strip())),
        rejected=rejected,
    )


# «Регламент не содержит…», «скидка не регламентирована» - это не факт из регламента, а признание пробела.
# Такое утверждение нельзя показывать как правило с цитатой: оно уходит в «чего нет в регламенте», ответ - неполный.
_ABSENCE = re.compile(
    r"(?:регламент\w*|источник\w*|пункт\w*|документ\w*)\s+не\s+(?:содерж|указ|описыв|регламентир|предусматр|уточня|определя)"
    r"|не\s+(?:регламентирован|указан|описан|определен|определён|предусмотрен|установлен)\w*"
    r"|(?:нет|отсутству\w*)\s+(?:информаци|сведени|требовани|данных|указани)",
    re.IGNORECASE,
)


def _is_absence(text: str) -> bool:
    return bool(_ABSENCE.search(text))


def _split_absence(variant: Variant, kept: list[Claim]) -> tuple[list[Claim], list[str]]:
    facts = [c for c in kept if not _is_absence(c.text)]
    gaps = [c.text for c in kept if _is_absence(c.text)]
    sentences = re.split(r"(?<=[.!?])\s+", variant.lead.strip()) if variant.lead else []
    gaps += [s for s in sentences if _is_absence(s)]
    return facts, gaps


def _restatus(variant: Variant, kept: list[Claim], *, dropped: int) -> Variant:
    kept, gaps = _split_absence(variant, kept)
    if gaps:
        gap = "; ".join(dict.fromkeys(g.rstrip(".") for g in ([variant.gap] if variant.gap else []) + gaps))
        lead = " ".join(s for s in re.split(r"(?<=[.!?])\s+", variant.lead.strip()) if s and not _is_absence(s))
        variant = variant.model_copy(
            update={"gap": gap, "lead": lead, "status": Status.PARTIAL if kept else Status.NOT_FOUND}
        )
        if kept:
            return _restatus_facts(variant, kept, dropped=dropped)
    return _restatus_facts(variant, kept, dropped=dropped)


def _restatus_facts(variant: Variant, kept: list[Claim], *, dropped: int) -> Variant:
    if not kept:
        return Variant(
            department_id=variant.department_id,
            status=Status.NOT_FOUND,
            gap=variant.gap or ("утверждения ответа не подтвердились текстом регламента" if dropped else None),
        )
    status = variant.status
    gap = variant.gap
    if status is Status.NOT_FOUND or (dropped and status is Status.ANSWERED):
        status = Status.PARTIAL
    if dropped and not gap:
        gap = "часть ответа модели не подтвердилась дословной цитатой регламента и скрыта"
    if status is Status.PARTIAL and not gap:
        gap = "регламент отвечает на вопрос не полностью - уточните недостающее в службе качества"
    lead = variant.lead if _lead_supported(variant.lead, kept) else ""
    # Короткая фраза-ответ не должна терять исключение правила («нельзя» вместо «нельзя, кроме RFI»).
    if lead and any(dropped_condition(lead, c.quote) for c in kept):
        lead = ""
    return variant.model_copy(update={"claims": kept, "status": status, "lead": lead, "gap": gap})


def _same_facts(answered: list[Variant]) -> bool:
    """Ответы одинаковые, только если совпадают числа цитат и смысл утверждений (пересечение лемм)."""
    if len(answered) < 2:
        return True
    fact_sets = [frozenset().union(*(numbers(c.quote) for c in v.claims)) for v in answered]
    if len(set(fact_sets)) != 1:
        return False
    texts = [" ".join(c.text for c in v.claims) for v in answered]
    return not any(texts_differ(texts[0], other) for other in texts[1:])


def merge_compositions(parts: list[VerifiedComposition]) -> VerifiedComposition:
    """Объединяет ответы, подготовленные для каждого подразделения отдельно (параллельные вызовы модели).
    Одинаковость ответов решает код - модель видела только своё подразделение."""
    variants = [v for p in parts for v in p.variants]
    answered = [v for v in variants if v.status is not Status.NOT_FOUND]
    conflict = next((p.conflict for p in parts if p.conflict is not None), None)
    missing = list(dict.fromkeys(m for p in parts for m in p.missing_documents))
    return VerifiedComposition(
        variants=variants,
        same_across_departments=_same_facts(answered),
        conflict=conflict,
        missing_documents=missing,
        rejected=[r for p in parts for r in p.rejected],
    )


def _valid_conflict(conflict: Conflict | None, allowed: dict[str, dict[str, str]]) -> Conflict | None:
    if conflict is None:
        return None
    for texts in allowed.values():
        if len(conflict.source_ids) >= 2 and all(sid in texts for sid in conflict.source_ids):
            return conflict
    return None


def lost_conditions(out: VerifiedComposition, inp: ComposeInput) -> list[str]:
    """Замечания модели: утверждение опирается на начало правила, а второе условие или исключение потеряно."""
    allowed = _allowed_sources(inp)
    notes: list[str] = []
    for variant in out.variants:
        quotes = [c.quote for c in variant.claims]
        for claim in variant.claims:
            others = [q for q in quotes if q is not claim.quote]
            rest = lost_condition(claim.quote, allowed[variant.department_id][claim.source_id], others)
            rest = rest or _dropped_in_text(claim, variant.claims)
            if rest:
                notes.append(
                    f"{variant.department_id}: утверждение «{claim.text}» ({claim.source_id}) неполное - "
                    f"в источнике правило продолжается: «{rest}». Включи это условие в утверждение и цитату."
                )
    return notes


def complete_conditions(out: VerifiedComposition, inp: ComposeInput) -> VerifiedComposition:
    """Если модель так и не дописала условие - утверждением становится само предложение регламента целиком.
    Дословный текст источника не искажает правило, в отличие от его половины."""
    allowed = _allowed_sources(inp)
    variants: list[Variant] = []
    for variant in out.variants:
        quotes = [c.quote for c in variant.claims]
        claims: list[Claim] = []
        for claim in variant.claims:
            text = allowed[variant.department_id][claim.source_id]
            others = [q for q in quotes if q is not claim.quote]
            if lost_condition(claim.quote, text, others) or _dropped_in_text(claim, variant.claims):
                sentence = full_sentence(claim.quote, text)
                claim = claim.model_copy(update={"text": sentence, "quote": sentence})
            claims.append(claim)
        variants.append(variant.model_copy(update={"claims": claims}))
    return out.model_copy(update={"variants": variants})


def _dropped_in_text(claim: Claim, siblings: list[Claim]) -> str | None:
    """Условие есть в цитате, но утверждение (и соседние утверждения того же ответа) его не передают."""
    rest = dropped_condition(claim.text, claim.quote)
    if rest is None:
        return None
    together = " ".join(c.text for c in siblings)
    return dropped_condition(together, claim.quote)


# «Кто назначает РП и нужно ли согласовывать его с заказчиком?» - вторая часть начинается с вопросительного слова.
_SECOND_PART = re.compile(
    r"\s(?:и|а также|а)\s+(?=(?:нужно ли|надо ли|можно ли|должен ли|должна ли|обязан ли|кто|какой|какая|какие|какую|"
    r"каким|сколько|когда|как|где|куда|в какой|в каком|в какие|чем)\b)",
    re.IGNORECASE,
)
_MIN_PART_COVERAGE = 0.34


def _uncovered_parts(variant: Variant, question: str) -> Variant:
    """Часть составного вопроса, о которой нет ни слова в утверждениях, - это пробел, а не молчаливый пропуск.

    Модель иногда отвечает только на первую часть и ставит «ответ найден»; код это видит по словам вопроса.
    """
    if variant.status is not Status.ANSWERED or not variant.claims:
        return variant
    parts = _SECOND_PART.split(question.strip().rstrip("?"))
    if len(parts) < 2:
        return variant
    said = set(lemmas(" ".join(f"{c.text} {c.quote}" for c in variant.claims)))
    missing = []
    for part in parts[1:]:
        words = {w for w in lemmas(part) if len(w) > 3}
        if words and len(words & said) / len(words) < _MIN_PART_COVERAGE:
            missing.append(part.strip())
    if not missing:
        return variant
    gap = "в регламентах нет ответа на часть вопроса: " + "; ".join(f"«{m}»" for m in missing)
    return variant.model_copy(update={"status": Status.PARTIAL, "gap": gap})
