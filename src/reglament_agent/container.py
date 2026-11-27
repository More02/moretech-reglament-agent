"""Сборка приложения: настройки → адаптеры → сервисы. Единственное место, где выбираются реализации портов."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from answer_compose.fake import HANDLERS as COMPOSE_FAKE
from answer_verify.fake import HANDLERS as VERIFY_FAKE
from clarification_extract.fake import HANDLERS as EXTRACT_FAKE
from expert_reply_classify.fake import HANDLERS as CLASSIFY_FAKE
from gap_cluster.fake import HANDLERS as CLUSTER_FAKE
from pii_guard import PiiGuard
from query_understand.fake import HANDLERS as UNDERSTAND_FAKE
from reglament_agent.adapters.db import Base, make_engine, make_session_factory
from reglament_agent.adapters.embeddings import make_embedder
from reglament_agent.adapters.llm_gateway import OpenAICompatibleLLM, Pricing
from reglament_agent.adapters.mail import ImapSmtpMailbox, MailTransport, MemoryMailbox
from reglament_agent.config import Settings
from reglament_agent.passport import Passport
from reglament_agent.services.analytics import Analytics
from reglament_agent.services.answer_agent import AnswerAgent
from reglament_agent.services.gardener import Gardener
from reglament_agent.services.knowledge import KnowledgeBase
from reglament_agent.services.mail_agent import MailAgent
from reglament_agent.services.retrieval import HybridIndex
from reglament_agent.services.usage import UsageLedger
from skill_sdk import FakeLLM, LLMClient

log = logging.getLogger(__name__)

FAKE_HANDLERS = {
    **UNDERSTAND_FAKE,
    **COMPOSE_FAKE,
    **VERIFY_FAKE,
    **CLASSIFY_FAKE,
    **EXTRACT_FAKE,
    **CLUSTER_FAKE,
}


@dataclass
class Container:
    settings: Settings
    passport: Passport
    sessions: sessionmaker[Session]
    llm: LLMClient
    mail_transport: MailTransport
    index: HybridIndex
    kb: KnowledgeBase
    mail: MailAgent
    agent: AnswerAgent
    analytics: Analytics
    gardener: Gardener
    ledger: UsageLedger


def build_container(settings: Settings, *, mail_transport: MailTransport | None = None) -> Container:
    passport = Passport.load(settings.passport_path)
    engine = make_engine(settings.database_url)
    if settings.db_auto_create:
        Base.metadata.create_all(engine)
    sessions = make_session_factory(engine)
    ledger = UsageLedger(sessions)

    llm: LLMClient
    judge_llm: LLMClient
    if settings.llm_fake or not settings.llm_api_key:
        if not settings.llm_fake:
            log.warning("LLM_API_KEY не задан - работаю на тестовой модели")
        llm = judge_llm = FakeLLM(FAKE_HANDLERS)
    else:

        def gateway(model: str, price_in: float, price_out: float) -> OpenAICompatibleLLM:
            return OpenAICompatibleLLM(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=model,
                pricing=Pricing(price_in, price_out, settings.usd_rub),
                pii=PiiGuard(enabled=settings.pii_masking),
                timeout=settings.llm_timeout_seconds,
                spent_today=ledger.spent_today,
                daily_budget_rub=settings.llm_daily_budget_rub,
                on_usage=ledger.record,
            )

        llm = gateway(settings.llm_model, settings.llm_price_input_usd_per_m, settings.llm_price_output_usd_per_m)
        judge_llm = gateway(
            settings.judge_model, settings.judge_price_input_usd_per_m, settings.judge_price_output_usd_per_m
        )

    if mail_transport is None:
        if settings.mail_backend == "imap":
            mail_transport = ImapSmtpMailbox(
                smtp_host=settings.mail_smtp_host,
                smtp_port=settings.mail_smtp_port,
                imap_host=settings.mail_imap_host,
                imap_port=settings.mail_imap_port,
                user=settings.mail_user,
                password=settings.mail_password,
            )
        else:
            mail_transport = MemoryMailbox(settings.mail_user or "agent@example.ru")

    embedder = make_embedder(
        settings.embeddings_backend,
        settings.embeddings_model,
        settings.embeddings_device,
        settings.embeddings_cache_path,
    )
    index = HybridIndex(embedder, passport.build_glossary())
    kb = KnowledgeBase(sessions, passport, embedder, index)
    mail = MailAgent(
        sessions=sessions,
        transport=mail_transport,
        passport=passport,
        kb=kb,
        llm=llm,
        quality_email=settings.quality_email,
        authorized=settings.authorized_senders(),
        public_base_url=settings.public_base_url,
        on_usage=ledger.record_context,
    )
    agent = AnswerAgent(
        sessions=sessions,
        passport=passport,
        index=index,
        kb=kb,
        mail=mail,
        llm=llm,
        strict_verify=settings.strict_verify,
        judge_llm=judge_llm,
        on_usage=ledger.record_context,
        document_url=lambda doc_id: f"{settings.public_base_url.rstrip('/')}/api/documents/{doc_id}",
    )
    analytics = Analytics(sessions, passport)
    gardener = Gardener(
        sessions=sessions,
        passport=passport,
        kb=kb,
        llm=llm,
        mail=mail_transport,
        quality_email=settings.quality_email,
        on_usage=ledger.record_context,
    )
    kb.rebuild_index()
    return Container(
        settings, passport, sessions, llm, mail_transport, index, kb, mail, agent, analytics, gardener, ledger
    )
