"""Проверка ответа кодом: источник, цитата, числа, статусы, одинаковость вариантов."""

from __future__ import annotations

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
from evidence import numbers, verify_claim


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
        variants.append(_restatus(variant, kept, dropped=len(variant.claims) - len(kept)))
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


def _restatus(variant: Variant, kept: list[Claim], *, dropped: int) -> Variant:
    if not kept:
        return Variant(
            department_id=variant.department_id,
            status=Status.NOT_FOUND,
            gap=variant.gap or ("утверждения ответа не подтвердились текстом регламента" if dropped else None),
        )
    status = variant.status
    if status is Status.NOT_FOUND or (dropped and status is Status.ANSWERED):
        status = Status.PARTIAL
    lead = variant.lead if _lead_supported(variant.lead, kept) else ""
    return variant.model_copy(update={"claims": kept, "status": status, "lead": lead})


def _same_facts(answered: list[Variant]) -> bool:
    """Модель могла сказать «одинаково», а сроки разные: тогда считаем ответы разными."""
    if len(answered) < 2:
        return True
    fact_sets = [frozenset().union(*(numbers(c.quote) for c in v.claims)) for v in answered]
    return len(set(fact_sets)) == 1


def _valid_conflict(conflict: Conflict | None, allowed: dict[str, dict[str, str]]) -> Conflict | None:
    if conflict is None:
        return None
    for texts in allowed.values():
        if len(conflict.source_ids) >= 2 and all(sid in texts for sid in conflict.source_ids):
            return conflict
    return None
