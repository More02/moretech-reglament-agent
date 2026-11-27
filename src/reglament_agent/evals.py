"""Прогон тестового набора: поведение, цитаты, ложные ответы, время и стоимость. Отчёт - JSON и Markdown."""

from __future__ import annotations

import json
import logging
import statistics
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from answer_verify import AnswerVerify, ClaimToCheck, VerifyInput
from reglament_agent.adapters.mail import MemoryMailbox
from reglament_agent.config import ROOT, Settings
from reglament_agent.container import Container, build_container
from reglament_agent.domain import AgentReply, Profile, ReplyKind
from skill_sdk import SkillContext

log = logging.getLogger(__name__)
CASES = ROOT / "evals" / "questions.yaml"
REPORTS = ROOT / "evals" / "reports"
ANSWER_KINDS = {ReplyKind.ANSWER}
SAFE_REFUSALS = {ReplyKind.NOT_FOUND, ReplyKind.CONFLICT, ReplyKind.ESCALATION_SENT}


@dataclass
class CaseResult:
    id: str
    question: str
    expect: str
    got: str
    behavior_ok: bool
    citation_ok: bool | None
    false_answer: bool
    missing_ok: bool | None
    latency_ms: int
    cost_rub: float
    llm_calls: int
    cited: list[str] = field(default_factory=list)
    judge_failed: list[str] = field(default_factory=list)
    note: str = ""


def _cited(reply: AgentReply, department: str | None = None) -> set[str]:
    return {c.source_id for v in reply.variants if department in (None, v.department_id) for c in v.claims}


def _citation_ok(reply: AgentReply, expected: dict[str, list[str]]) -> bool:
    return all(_cited(reply, dep) & set(ids) for dep, ids in expected.items())


def _run_case(c: Container, case: dict[str, Any]) -> CaseResult:
    profile = Profile(name="Тестовый сотрудник", email="tester@example.ru", department=case.get("department"))
    conv = c.agent.start(profile)
    started = time.perf_counter()
    reply = c.agent.ask(conv, case["q"])
    expect = case["expect"]
    first_kind = reply.kind.value
    total_cost, total_calls = reply.usage.cost_rub, reply.usage.llm_calls
    behavior_ok = reply.kind.value == expect or reply.kind.value in case.get("also_ok", [])
    citation_ok: bool | None = None
    note = ""
    if expect == "clarify" and behavior_ok:
        offered = {o.id.removeprefix("dep:") for o in reply.options if o.id.startswith("dep:")}
        missing_opts = set(case.get("options", [])) - offered
        if missing_opts:
            behavior_ok = False
            note = f"нет кнопок: {sorted(missing_opts)}"
        if case.get("choose"):
            follow = c.agent.choose(conv, f"dep:{case['choose']}")
            total_cost += follow.usage.cost_rub
            total_calls += follow.usage.llm_calls
            citation_ok = _citation_ok(follow, {case["choose"]: case["clauses"][case["choose"]]})
            reply = follow
    elif expect == "answer" and case.get("clauses"):
        citation_ok = behavior_ok and _citation_ok(reply, case["clauses"])
    false_answer = expect in ("not_found", "out_of_scope", "off_task") and reply.kind in ANSWER_KINDS
    missing_ok = bool(reply.missing_documents) if case.get("missing") else None
    return CaseResult(
        id=case["id"],
        question=case["q"],
        expect=expect,
        got=first_kind,
        behavior_ok=behavior_ok,
        citation_ok=citation_ok,
        false_answer=false_answer,
        missing_ok=missing_ok,
        latency_ms=int((time.perf_counter() - started) * 1000),
        cost_rub=round(total_cost, 4),
        llm_calls=total_calls,
        cited=sorted(_cited(reply)),
        note=note or (reply.text[:160] if not behavior_ok else ""),
    )


def _judge(c: Container, case: CaseResult, reply_claims: list[tuple[str, str]]) -> list[str]:
    """Независимая модель проверяет, что утверждения не искажают источник (answer-verify)."""
    claims = []
    for i, (text, source_id) in enumerate(reply_claims):
        unit = c.index.unit(source_id)
        if unit:
            claims.append(ClaimToCheck(id=str(i), text=text, source_text=unit.text))
    if not claims:
        return []
    out = AnswerVerify().run(VerifyInput(question=case.question, claims=claims), SkillContext(llm=c.llm))
    return sorted(out.failed_ids())


def _summary(results: list[CaseResult], seconds: float) -> dict[str, Any]:
    def share(values: list[bool]) -> float | None:
        return round(sum(values) / len(values), 3) if values else None

    answered = [r for r in results if r.expect in ("answer", "clarify")]
    refusals = [r for r in results if r.expect in ("not_found", "out_of_scope", "off_task")]
    latencies = [r.latency_ms for r in results if r.llm_calls]
    by_cat: dict[str, list[CaseResult]] = {}
    for r in results:
        by_cat.setdefault(r.id[0], []).append(r)
    return {
        "cases": len(results),
        "behavior_accuracy": share([r.behavior_ok for r in results]),
        "citation_accuracy": share([bool(r.citation_ok) for r in answered if r.citation_ok is not None]),
        "false_answer_rate": share([r.false_answer for r in refusals]),
        "escalation_recall": share(
            [r.got in {k.value for k in SAFE_REFUSALS} for r in results if r.expect == "not_found"]
        ),
        "clarify_recall": share([r.got == "clarify" for r in results if r.expect == "clarify"]),
        "missing_docs_flagged": share([bool(r.missing_ok) for r in results if r.missing_ok is not None]),
        "judge_distortions": sum(len(r.judge_failed) for r in results),
        "latency_ms_p50": int(statistics.median(latencies)) if latencies else 0,
        "latency_ms_p95": int(sorted(latencies)[int(len(latencies) * 0.95) - 1]) if latencies else 0,
        "avg_cost_rub": round(sum(r.cost_rub for r in results) / len(results), 4) if results else 0.0,
        "avg_llm_calls": round(sum(r.llm_calls for r in results) / len(results), 2) if results else 0.0,
        "by_category": {k: share([r.behavior_ok and r.citation_ok is not False for r in v]) for k, v in by_cat.items()},
        "duration_s": round(seconds, 1),
    }


def run_eval(settings: Settings, *, limit: int = 0, judge: bool = False) -> float:
    """Прогоняет набор на свежей базе и настоящих регламентах. Возвращает долю верного поведения."""
    cases: list[dict[str, Any]] = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]
    if limit:
        cases = cases[:limit]
    with tempfile.TemporaryDirectory() as tmp:
        cfg = settings.model_copy(
            update={"database_url": f"sqlite:///{Path(tmp) / 'eval.db'}", "mail_backend": "memory"}
        )
        c = build_container(cfg, mail_transport=MemoryMailbox())
        c.kb.ingest(c.kb.parse_directory(cfg.regulations_dir))
        _check_case_ids(c, cases)
        started = time.perf_counter()
        results: list[CaseResult] = []
        for case in cases:
            r = _run_case(c, case)
            if judge and r.cited:
                r.judge_failed = _judge_last(c, r)
            results.append(r)
            log.info(
                "%s %s → %s %s", r.id, r.expect, r.got, "OK" if r.behavior_ok and r.citation_ok is not False else "FAIL"
            )
        summary = _summary(results, time.perf_counter() - started)
    summary["model"] = "fake" if cfg.llm_fake else cfg.llm_model
    _write(summary, results)
    return float(summary["behavior_accuracy"] or 0.0)


def _judge_last(c: Container, r: CaseResult) -> list[str]:
    with c.sessions() as s:
        from sqlalchemy import select

        from reglament_agent.adapters.db import TurnRow

        last = s.scalars(select(TurnRow).where(TurnRow.role == "agent").order_by(TurnRow.id.desc())).first()
        payload = last.payload if last else {}
    claims = [(cl["text"], cl["source_id"]) for v in payload.get("variants", []) for cl in v["claims"]]
    return _judge(c, r, claims)


def _check_case_ids(c: Container, cases: list[dict[str, Any]]) -> None:
    unknown = [
        cid for case in cases for ids in (case.get("clauses") or {}).values() for cid in ids if not c.index.unit(cid)
    ]
    if unknown:
        raise ValueError(f"в наборе есть несуществующие пункты: {unknown}")


def _write(summary: dict[str, Any], results: list[CaseResult]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    payload = {"summary": summary, "results": [asdict(r) for r in results]}
    (REPORTS / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Отчёт тестового прогона", "", "| Метрика | Значение |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in summary.items() if k != "by_category"]
    lines += ["", "| id | ожидали | получили | поведение | цитата | ₽ | мс |", "|---|---|---|---|---|---|---|"]
    for r in results:
        cit = "-" if r.citation_ok is None else ("да" if r.citation_ok else "нет")
        ok = "да" if r.behavior_ok else "нет"
        lines.append(f"| {r.id} | {r.expect} | {r.got} | {ok} | {cit} | {r.cost_rub} | {r.latency_ms} |")
    (REPORTS / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
