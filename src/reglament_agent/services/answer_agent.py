"""Агент ответов: профиль → понимание → поиск с квотами → ответы с цитатами → проверка → решение.

Решения о том, уточнять ли подразделение, предлагать ли службу качества и что показывать, принимает код по
правилам ниже, а не модель. Модель только разбирает вопрос и формулирует утверждения с цитатами.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from answer_compose import (
    AnswerCompose,
    ComposeInput,
    DepartmentSources,
    ExpertNote,
    Source,
    Status,
    Variant,
    VerifiedComposition,
    merge_compositions,
)
from answer_verify import AnswerVerify, ClaimToCheck, VerifyInput
from query_understand import DepartmentRef, Intent, QueryUnderstand, Turn, Understanding, UnderstandInput
from reglament_agent.adapters.db import ConversationRow, TurnRow
from reglament_agent.domain import (
    AgentReply,
    ClaimView,
    DocumentView,
    Option,
    Profile,
    ReplyKind,
    TicketView,
    UsageView,
    VariantView,
)
from reglament_agent.passport import Passport
from reglament_agent.services.knowledge import KnowledgeBase
from reglament_agent.services.mail_agent import MailAgent
from reglament_agent.services.retrieval import Hit, HybridIndex
from ru_text import lemmas
from skill_sdk import LLMClient, LLMError, SkillContext

log = logging.getLogger(__name__)

OPT_ALL = "all"
OPT_COMPLEX = "complex"
OPT_ESCALATE = "escalate"
OPT_OTHER_DEPS = "other_departments"
DEP_PREFIX = "dep:"
NOT_SURE = ("не знаю", "незнаю", "не уверен", "без разницы", "все", "всех", "покажи все")


@dataclass
class TurnContext:
    conversation_id: str
    profile: Profile
    state: dict[str, Any]
    history: list[Turn]
    skill_ctx: SkillContext
    started: float
    # Проверка кодом в этом ходе: сколько утверждений модели проверено и сколько отброшено.
    checked_claims: int = 0
    rejected_claims: int = 0


class AnswerAgent:
    def __init__(
        self,
        *,
        sessions: sessionmaker[Session],
        passport: Passport,
        index: HybridIndex,
        kb: KnowledgeBase,
        mail: MailAgent,
        llm: LLMClient,
        strict_verify: bool = False,
        judge_llm: LLMClient | None = None,
        on_usage: Callable[[SkillContext], None] = lambda _c: None,
        document_url: Callable[[str], str] = lambda doc_id: f"/documents/{doc_id}",
    ) -> None:
        self.sessions = sessions
        self.passport = passport
        self.index = index
        self.kb = kb
        self.mail = mail
        self.llm = llm
        self.strict_verify = strict_verify
        # Проверяющий - другая, более крупная модель: независимость от того, кто формулировал ответ.
        self.judge_llm = judge_llm or llm
        self.on_usage = on_usage
        self.document_url = document_url
        self.glossary = passport.build_glossary()
        self.understand_skill = QueryUnderstand()
        self.compose_skill = AnswerCompose()
        self.verify_skill = AnswerVerify()

    # ================= публичные методы =================

    def start(self, profile: Profile) -> str:
        with self.sessions.begin() as s:
            conv = ConversationRow(profile=profile.model_dump(), state={})
            s.add(conv)
            s.flush()
            return conv.id

    def ask(self, conversation_id: str, text: str) -> AgentReply:
        tc = self._load(conversation_id)
        self._save_turn(tc, "employee", text)
        try:
            pending_choice = self._match_pending_choice(tc, text)
            reply = self._choose(tc, pending_choice) if pending_choice else self._answer_question(tc, text)
        except LLMError as exc:
            log.exception("ошибка модели")
            reply = AgentReply(
                kind=ReplyKind.ERROR,
                text=f"Не получилось ответить: модель недоступна ({exc}). Попробуйте ещё раз через минуту.",
            )
        return self._finish(tc, reply)

    def choose(self, conversation_id: str, option_id: str) -> AgentReply:
        tc = self._load(conversation_id)
        label = next((o.label for o in self._last_options(tc) if o.id == option_id), option_id)
        self._save_turn(tc, "employee", label)
        try:
            reply = self._choose(tc, option_id)
        except LLMError as exc:
            reply = AgentReply(kind=ReplyKind.ERROR, text=f"Не получилось: модель недоступна ({exc}).")
        return self._finish(tc, reply)

    def rate(self, turn_id: int, rating: int) -> None:
        with self.sessions.begin() as s:
            turn = s.get(TurnRow, turn_id)
            if turn is not None:
                turn.rating = rating

    # ================= вопрос =================

    def _answer_question(self, tc: TurnContext, text: str) -> AgentReply:
        hits = {g.canonical: g.canonical for g in self.glossary.find(text)}
        glossary_hits = {alias: g.canonical for g in self.glossary.find(text) for alias in g.aliases if alias in text}
        understanding = self.understand_skill.run(
            UnderstandInput(
                question=text,
                history=tc.history[-6:],
                departments=[DepartmentRef(id=d.id, name=d.name, aliases=d.aliases) for d in self.passport.departments],
                glossary_hits=glossary_hits or hits,
                out_of_scope_topics=[o.topic for o in self.passport.out_of_scope],
            ),
            tc.skill_ctx,
        )
        tc.state["pending"] = None
        tc.state["last_question"] = understanding.standalone_question
        match understanding.intent:
            case Intent.GREETING:
                return self._greeting()
            case Intent.OFF_TASK:
                return AgentReply(
                    kind=ReplyKind.OFF_TASK,
                    text=(
                        "Я отвечаю только на вопросы по регламентам компании и не выполняю другие задачи. "
                        "Спросите, например, кто согласует расчёт трудозатрат или можно ли начать работы без договора."
                    ),
                )
            case Intent.OUT_OF_SCOPE:
                topic = self.passport.out_of_scope[understanding.out_of_scope_topic or 0]
                return AgentReply(kind=ReplyKind.OUT_OF_SCOPE, text=topic.redirect)
            case Intent.FIND_DOCUMENT:
                return self._find_documents(understanding)
            case _:
                return self._regulation_answer(tc, understanding)

    def _target_departments(self, tc: TurnContext, u: Understanding) -> tuple[list[str], str | None]:
        """Подразделения для ответа и откуда известно подразделение ('question' | 'profile' | 'dialog' | None)."""
        if u.departments:
            return u.departments, "question"
        if tc.state.get("department"):
            return [tc.state["department"]], "dialog"
        if tc.profile.department:
            return [tc.profile.department], "profile"
        return [d.id for d in self.passport.departments], None

    def _regulation_answer(self, tc: TurnContext, u: Understanding) -> AgentReply:
        departments, known_from = self._target_departments(tc, u)
        composition, hits = self._compose(tc, u, departments)
        tc.state["pending"] = {
            "question": u.standalone_question,
            "process": u.process.value if u.process else None,
            "composition": composition.model_dump(mode="json"),
            "clause_ids": [h.unit.id for hs in hits.values() for h in hs if h.unit.kind == "clause"],
            "departments": departments,
            "complex": u.complex_project,
        }
        missing = self._missing_documents(composition, hits)
        answered = composition.answered()

        if composition.conflict is not None:
            return self._conflict_reply(composition, missing)
        if not answered:
            return self._not_found_reply(tc, u.standalone_question, missing)
        if known_from is not None or len(departments) == 1:
            return self._known_department_reply(tc, composition, departments, known_from, missing)
        if len(answered) == 1 or composition.same_across_departments:
            return self._show_variants(tc, composition, answered, missing, header=self._same_header(answered))
        if u.complex_project:
            return self._show_variants(
                tc,
                composition,
                answered,
                missing,
                header="Комплексный проект: требования каждого подразделения - отдельно.",
            )
        return self._clarify(tc, answered, missing)

    def _compose(
        self, tc: TurnContext, u: Understanding, departments: list[str]
    ) -> tuple[VerifiedComposition, dict[str, list[Hit]]]:
        process = u.process.value if u.process else None
        hits = self.index.search(u.search_queries, departments=departments, per_department=6, process=process)
        note_hits = self.index.search(u.search_queries, departments=departments, per_department=2, kind="note")
        dep_sources = []
        for dep in departments:
            units = self._expand_sections([h.unit for h in hits.get(dep, [])])
            dep_sources.append(
                DepartmentSources(
                    id=dep,
                    name=self.passport.department(dep).name,
                    sources=[Source(id=un.id, ref=un.title, path=[], text=un.text) for un in units],
                )
            )
        notes = {}
        for dep_hits in note_hits.values():
            for h in dep_hits:
                if h.dense_score >= 0.35 or (h.bm25_rank is not None and h.bm25_rank < 3):
                    notes[h.unit.id] = ExpertNote(
                        id=h.unit.id,
                        question=h.unit.search_text.split("\n")[0],
                        answer=h.unit.text,
                        department_ids=list(h.unit.departments),
                        date=h.unit.title.rsplit(" ", 1)[-1],
                    )
        inp = ComposeInput(question=u.standalone_question, departments=dep_sources, expert_notes=list(notes.values()))
        composition = self._compose_parallel(inp, tc)
        tc.checked_claims = sum(len(v.claims) for v in composition.variants) + len(composition.rejected)
        tc.rejected_claims = len(composition.rejected)
        if self.strict_verify:
            composition = self._strict(tc, inp, composition)
        return composition, hits

    def _compose_parallel(self, inp: ComposeInput, tc: TurnContext) -> VerifiedComposition:
        """По вызову модели на подразделение, одновременно: время ответа не растёт с числом подразделений,
        а короткий контекст одного подразделения не даёт модели смешивать правила разных дирекций."""
        parts = [inp.model_copy(update={"departments": [dep]}) for dep in inp.departments if dep.sources]
        if len(parts) <= 1:
            return (
                self.compose_skill.run(parts[0], tc.skill_ctx) if parts else self.compose_skill.run(inp, tc.skill_ctx)
            )
        with ThreadPoolExecutor(max_workers=len(parts)) as pool:
            results = list(pool.map(lambda part: self.compose_skill.run(part, tc.skill_ctx), parts))
        composed = merge_compositions(results)
        empty = [d.id for d in inp.departments if not d.sources]
        return composed.model_copy(
            update={
                "variants": [*composed.variants, *(Variant(department_id=d, status=Status.NOT_FOUND) for d in empty)]
            }
        )

    def _expand_sections(self, units: list[Any]) -> list[Any]:
        """Найденный заголовок раздела без текста дополняем его пунктами - иначе модели не на что опереться."""
        out: dict[str, Any] = {}
        for un in units:
            out.setdefault(un.id, un)
            if len(un.text) < 220:
                for child in self.index.children_of(un)[:6]:
                    out.setdefault(child.id, child)
        return list(out.values())[:12]

    def _strict(self, tc: TurnContext, inp: ComposeInput, comp: VerifiedComposition) -> VerifiedComposition:
        texts = {s.id: s.text for d in inp.departments for s in d.sources} | {n.id: n.answer for n in inp.expert_notes}
        claims = [
            ClaimToCheck(id=f"{vi}:{ci}", text=c.text, source_text=texts.get(c.source_id, ""))
            for vi, v in enumerate(comp.variants)
            for ci, c in enumerate(v.claims)
        ]
        judge_ctx = replace(tc.skill_ctx, llm=self.judge_llm)
        failed = self.verify_skill.run(VerifyInput(question=inp.question, claims=claims), judge_ctx).failed_ids()
        variants = []
        for vi, v in enumerate(comp.variants):
            kept = [c for ci, c in enumerate(v.claims) if f"{vi}:{ci}" not in failed]
            if len(kept) != len(v.claims):
                v = v.model_copy(update={"claims": kept, "status": Status.PARTIAL if kept else Status.NOT_FOUND})
            variants.append(v)
        return comp.model_copy(update={"variants": variants})

    def _missing_documents(self, comp: VerifiedComposition, hits: dict[str, list[Hit]]) -> list[str]:
        """Отсутствующие документы, на которые ссылаются пункты ответа. Если ответа нет - только те, что модель
        назвала нужными для ответа и которые действительно упомянуты в найденных пунктах (сверка кодом)."""
        cited = [c.source_id for v in comp.variants for c in v.claims if not c.source_id.startswith("note:")]
        if cited:
            return self.kb.missing_references(cited)
        if not comp.missing_documents:
            return []
        found = self.kb.missing_references([h.unit.id for hs in hits.values() for h in hs])
        named = [lemmas(m) for m in comp.missing_documents]
        return [f for f in found if any(set(n) & set(lemmas(f)) >= set(n[:2]) for n in named if n)]

    # ================= ответы =================

    def _variant_view(self, v: Any) -> VariantView:
        claims = []
        for c in v.claims:
            unit = self.index.unit(c.source_id)
            claims.append(
                ClaimView(
                    text=c.text,
                    source_id=c.source_id,
                    source_title=unit.title if unit else c.source_id,
                    quote=c.quote,
                    from_quality=c.source_id.startswith("note:"),
                )
            )
        return VariantView(
            department_id=v.department_id,
            department_name=self.passport.department(v.department_id).name,
            status=v.status.value,
            lead=v.lead,
            claims=claims,
            steps=v.steps,
            gap=v.gap,
        )

    def _show_variants(
        self, tc: TurnContext, comp: VerifiedComposition, variants: list[Any], missing: list[str], *, header: str
    ) -> AgentReply:
        views = [self._variant_view(v) for v in variants]
        partial = any(v.status == "partial" for v in views)
        options = [Option(id=OPT_ESCALATE, label="Отправить вопрос в службу качества")] if partial else []
        text = header
        if any(c.from_quality for v in views for c in v.claims):
            text += (
                "\nОтвет опирается на разъяснение службы качества - оно приоритетнее текста регламента "
                "(регламент может быть на актуализации)."
            )
        if partial:
            text += (
                "\nПолного ответа в регламентах нет: ниже только то, что в них прямо написано, а чего нет - отмечено "
                "отдельно. Додумывать не буду - недостающую часть могу отправить в службу качества."
            )
        tc.state["clarifications"] = 0
        return AgentReply(
            kind=ReplyKind.ANSWER,
            text=text.strip(),
            variants=views,
            options=options,
            missing_documents=missing,
        )

    def _same_header(self, answered: list[Any]) -> str:
        if len(answered) == 1:
            return (
                f"Ответ есть в регламенте подразделения «{self.passport.department(answered[0].department_id).name}»."
            )
        names = ", ".join(self.passport.department(v.department_id).name for v in answered)
        return f"Правило одинаковое для подразделений: {names}."

    def _known_department_reply(
        self,
        tc: TurnContext,
        comp: VerifiedComposition,
        departments: list[str],
        known_from: str | None,
        missing: list[str],
    ) -> AgentReply:
        chosen = [v for v in comp.variants if v.department_id in departments]
        answered = [v for v in chosen if v.status is not Status.NOT_FOUND]
        names = ", ".join(self.passport.department(d).name for d in departments)
        source_note = {
            "profile": f"Отвечаю для подразделения «{names}» по вашему профилю.",
            "dialog": f"Отвечаю для подразделения «{names}».",
            "question": "",
        }.get(known_from or "", "")
        if not answered:
            return self._not_found_reply(tc, tc.state["pending"]["question"], missing, scope=names)
        reply = self._show_variants(
            tc,
            comp,
            answered,
            missing,
            header=source_note or ("Требования каждого подразделения - отдельно." if len(answered) > 1 else ""),
        )
        if known_from in ("profile", "dialog"):
            reply.options.append(Option(id=OPT_OTHER_DEPS, label="Показать для других подразделений"))
        return reply

    def _clarify(self, tc: TurnContext, answered: list[Any], missing: list[str]) -> AgentReply:
        count = int(tc.state.get("clarifications", 0))
        if count >= self.passport.dialog.max_clarifications:
            return self._show_variants(
                tc,
                VerifiedComposition.model_validate(tc.state["pending"]["composition"]),
                answered,
                missing,
                header="Показываю варианты для каждого подразделения.",
            )
        tc.state["clarifications"] = count + 1
        options = [
            Option(id=f"{DEP_PREFIX}{v.department_id}", label=self.passport.department(v.department_id).name)
            for v in answered
        ]
        options += [
            Option(id=OPT_ALL, label="Не знаю - показать все варианты"),
            Option(id=OPT_COMPLEX, label="Комплексный проект нескольких подразделений"),
        ]
        return AgentReply(
            kind=ReplyKind.CLARIFY,
            text="Ответ зависит от подразделения: правила в регламентах разные. В каком подразделении вы работаете "
            "или чей это проект?",
            options=options,
            missing_documents=missing,
        )

    def _conflict_reply(self, comp: VerifiedComposition, missing: list[str]) -> AgentReply:
        if comp.conflict is None:
            raise RuntimeError("нарушен инвариант: comp.conflict отсутствует")
        views = [self._variant_view(v) for v in comp.answered()]
        return AgentReply(
            kind=ReplyKind.CONFLICT,
            text="В регламенте есть пункты, которые для одного и того же случая говорят разное: "
            f"{comp.conflict.description} Выбирать между ними сам я не буду - лучше уточнить у службы качества.",
            variants=views,
            options=[Option(id=OPT_ESCALATE, label="Отправить вопрос в службу качества")],
            missing_documents=missing,
        )

    def _not_found_reply(self, tc: TurnContext, question: str, missing: list[str], scope: str = "") -> AgentReply:
        where = f" подразделения «{scope}»" if scope else ""
        text = f"В действующих регламентах{where} ответа на этот вопрос нет, а придумывать правило я не буду."
        if missing:
            text += " Регламенты ссылаются на документы, которых нет в базе: " + "; ".join(missing) + "."
        if self.passport.dialog.auto_send_escalation:
            return self._escalate(tc, question, prefix=text)
        options = [Option(id=OPT_ESCALATE, label="Отправить вопрос в службу качества")]
        if scope:
            options.append(Option(id=OPT_OTHER_DEPS, label="Посмотреть в регламентах других подразделений"))
        text += " Могу отправить вопрос в службу качества - вы будете в копии письма, а ответ я сохраню в базе знаний."
        return AgentReply(kind=ReplyKind.NOT_FOUND, text=text, options=options, missing_documents=missing)

    def _escalate(self, tc: TurnContext, question: str, prefix: str = "") -> AgentReply:
        pending = tc.state.get("pending") or {}
        labels = {o.label for o in self._last_options(tc)}
        context = "; ".join(
            t.text for t in tc.history[-6:] if t.role == "employee" and t.text != question and t.text not in labels
        )
        ticket = self.mail.escalate(
            conversation_id=tc.conversation_id,
            profile=tc.profile,
            question=question,
            context=context,
            candidate_clause_ids=pending.get("clause_ids", [])[:12],
        )
        tc.state["pending"] = None
        text = (f"{prefix} " if prefix else "") + (
            f"Отправил вопрос в службу качества: обращение {ticket.code}, вы в копии письма. "
            "Когда эксперт ответит, я пришлю ответ сюда и запомню его для похожих вопросов."
        )
        return AgentReply(
            kind=ReplyKind.ESCALATION_SENT,
            text=text.strip(),
            ticket=TicketView(code=ticket.code, status=ticket.status, quality_email=self.mail.quality_email),
        )

    def _find_documents(self, u: Understanding) -> AgentReply:
        hits = self.index.search(
            u.search_queries, departments=[d.id for d in self.passport.departments], per_department=3
        )
        docs: dict[str, DocumentView] = {}
        for dep, dep_hits in hits.items():
            for h in dep_hits[:1]:
                if h.unit.doc_id and h.unit.doc_id not in docs:
                    meta = self.passport.document(h.unit.doc_id)
                    docs[h.unit.doc_id] = DocumentView(
                        id=meta.id,
                        title=meta.title,
                        department_name=self.passport.department(dep).name,
                        url=self.document_url(meta.id),
                    )
        return AgentReply(
            kind=ReplyKind.DOCUMENT, text="Вот регламенты по теме вопроса:", documents=list(docs.values())
        )

    def _greeting(self) -> AgentReply:
        deps = ", ".join(d.name for d in self.passport.departments)
        return AgentReply(
            kind=ReplyKind.GREETING,
            text=f"Здравствуйте! Я {self.passport.assistant_name.lower()} компании {self.passport.company}. Отвечаю "
            f"на вопросы по пресейловой и проектной деятельности ({deps}) строго по тексту регламентов - с цитатами. "
            "Если ответа в регламентах нет, отправлю вопрос в службу качества.",
        )

    # ================= выбор варианта =================

    def _match_pending_choice(self, tc: TurnContext, text: str) -> str | None:
        """Ответ текстом на уточнение («ИБ», «не знаю») трактуем как выбор кнопки."""
        if not tc.state.get("pending") or not self._last_options(tc):
            return None
        low = text.strip().lower()
        if len(low) > 60:
            return None
        if any(low.startswith(n) for n in NOT_SURE):
            return OPT_ALL
        for d in self.passport.departments:
            if any(a.lower() == low or low.endswith(a.lower()) for a in [d.name, *d.aliases]):
                return f"{DEP_PREFIX}{d.id}"
        return None

    def _choose(self, tc: TurnContext, option_id: str) -> AgentReply:
        pending = tc.state.get("pending")
        if option_id == OPT_ESCALATE:
            question = pending["question"] if pending else tc.state.get("last_question", "")
            if not question:
                return AgentReply(
                    kind=ReplyKind.ERROR, text="Сначала задайте вопрос - я отправлю его в службу качества."
                )
            return self._escalate(tc, question)
        if not pending:
            return AgentReply(kind=ReplyKind.ERROR, text="Этот вариант уже неактуален - задайте вопрос ещё раз.")
        comp = VerifiedComposition.model_validate(pending["composition"])
        if option_id == OPT_OTHER_DEPS:
            u = Understanding(
                intent=Intent.REGULATION_QUESTION,
                standalone_question=pending["question"],
                search_queries=[pending["question"]],
            )
            all_deps = [d.id for d in self.passport.departments]
            comp, _ = self._compose(tc, u, all_deps)
            answered = comp.answered()
            if not answered:
                return self._not_found_reply(tc, pending["question"], [])
            return self._show_variants(tc, comp, answered, [], header="Ответы по регламентам всех подразделений:")
        answered = comp.answered()
        if option_id.startswith(DEP_PREFIX):
            dep = option_id.removeprefix(DEP_PREFIX)
            tc.state["department"] = dep
            if dep not in pending.get("departments", []):
                # Варианты считались для другого подразделения (например, из профиля) - готовим ответ для выбранного
                u = Understanding(
                    intent=Intent.REGULATION_QUESTION,
                    standalone_question=pending["question"],
                    search_queries=[pending["question"]],
                )
                comp, _ = self._compose(tc, u, [dep])
                answered = comp.answered()
            chosen = [v for v in answered if v.department_id == dep]
            if not chosen:
                return self._not_found_reply(tc, pending["question"], [], scope=self.passport.department(dep).name)
            return self._show_variants(
                tc, comp, chosen, [], header=f"Для подразделения «{self.passport.department(dep).name}»:"
            )
        header = (
            "Комплексный проект: требования каждого подразделения - отдельно, их нельзя смешивать."
            if option_id == OPT_COMPLEX
            else "Варианты для каждого подразделения:"
        )
        return self._show_variants(tc, comp, answered, [], header=header)

    # ================= состояние =================

    def _load(self, conversation_id: str) -> TurnContext:
        with self.sessions() as s:
            conv = s.get(ConversationRow, conversation_id)
            if conv is None:
                raise KeyError(conversation_id)
            turns = s.scalars(
                select(TurnRow).where(TurnRow.conversation_id == conversation_id).order_by(TurnRow.id)
            ).all()
            history = [Turn(role=t.role, text=t.text[:800]) for t in turns[-8:]]
            return TurnContext(
                conversation_id,
                Profile.model_validate(conv.profile),
                dict(conv.state or {}),
                history,
                SkillContext(llm=self.llm),
                time.perf_counter(),
            )

    def _last_options(self, tc: TurnContext) -> list[Option]:
        return [Option.model_validate(o) for o in tc.state.get("last_options", [])]

    def _save_turn(self, tc: TurnContext, role: str, text: str) -> None:
        with self.sessions.begin() as s:
            s.add(TurnRow(conversation_id=tc.conversation_id, role=role, text=text, outcome=""))
        tc.history.append(Turn(role=role, text=text))

    def _finish(self, tc: TurnContext, reply: AgentReply) -> AgentReply:
        meter = tc.skill_ctx.usage
        reply.usage = UsageView(
            input_tokens=meter.input_tokens,
            output_tokens=meter.output_tokens,
            cost_rub=meter.cost_rub,
            latency_ms=int((time.perf_counter() - tc.started) * 1000),
            llm_calls=len(meter.calls),
        )
        if reply.checked_claims == 0:
            reply.checked_claims, reply.rejected_claims = tc.checked_claims, tc.rejected_claims
        tc.state["last_options"] = [o.model_dump() for o in reply.options]
        self.on_usage(tc.skill_ctx)
        with self.sessions.begin() as s:
            conv = s.get(ConversationRow, tc.conversation_id)
            if conv is None:
                raise RuntimeError("нарушен инвариант: conv отсутствует")
            conv.state = tc.state
            row = TurnRow(
                conversation_id=tc.conversation_id,
                role="agent",
                text=reply.text,
                payload={},
                outcome=reply.kind.value,
                departments=[v.department_id for v in reply.variants],
                clause_ids=[c.source_id for v in reply.variants for c in v.claims],
                input_tokens=reply.usage.input_tokens,
                output_tokens=reply.usage.output_tokens,
                cost_rub=reply.usage.cost_rub,
                latency_ms=reply.usage.latency_ms,
            )
            s.add(row)
            s.flush()
            reply.turn_id = row.id
            row.payload = reply.model_dump(mode="json")
        return reply
