"""Настройки приложения из окружения (.env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Модель
    llm_base_url: str = "https://api.aitunnel.ru/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen3.6-35b-a3b"
    llm_timeout_seconds: float = 40.0
    llm_fake: bool = Field(default=False, description="Тестовая модель вместо настоящей (разработка, CI)")
    # Цены официального провайдера (Alibaba Cloud) для расчёта стоимости, $ за 1 млн токенов
    llm_price_input_usd_per_m: float = 0.375
    llm_price_output_usd_per_m: float = 2.25
    usd_rub: float = 82.313  # курс ЦБ РФ на 26.11.2026
    llm_daily_budget_rub: float = 500.0
    # Независимый проверяющий (строгий режим и оценка качества) - более крупная открытая модель
    judge_model: str = "qwen3.5-122b-a10b"
    judge_price_input_usd_per_m: float = 0.40
    judge_price_output_usd_per_m: float = 3.20
    strict_verify: bool = Field(default=False, description="Дополнительно проверять ответ второй моделью")

    # Эмбеддинги
    embeddings_model: str = "BAAI/bge-m3"
    embeddings_device: str = "cpu"
    embeddings_backend: str = Field(default="auto", description="auto | sentence-transformers | hashing")
    embeddings_cache_path: Path | None = ROOT / "data" / "cache" / "embeddings.sqlite"

    # Хранилище
    database_url: str = f"sqlite:///{ROOT / 'data' / 'reglament.db'}"
    db_auto_create: bool = Field(default=True, description="Создавать таблицы без миграций (разработка, тесты)")

    # Почта
    mail_backend: str = Field(default="memory", description="memory | imap")
    mail_smtp_host: str = ""
    mail_smtp_port: int = 465
    mail_imap_host: str = ""
    mail_imap_port: int = 993
    mail_user: str = ""
    mail_password: str = ""
    mail_poll_seconds: int = 30
    quality_email: str = "quality@example.ru"
    quality_authorized_senders: str = Field(default="", description="Адреса или @домены через запятую")

    # Паспорт и документы
    passport_path: Path = ROOT / "passports" / "softline.yaml"
    regulations_dir: Path = ROOT / "data" / "regulations"
    confluence_url: str = ""
    confluence_token: str = ""
    confluence_space: str = ""

    # ПДн и защита стенда
    pii_masking: bool = True
    rate_limit_per_minute: int = 20
    public_base_url: str = "http://localhost:8000"
    admin_token: str = ""

    def authorized_senders(self) -> list[str]:
        items = [s.strip().lower() for s in self.quality_authorized_senders.split(",") if s.strip()]
        return [*items, self.quality_email.lower()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
