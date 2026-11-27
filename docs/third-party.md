# Сторонние компоненты и ранее созданные наработки

## Ранее созданные наработки
Весь код репозитория написан в ходе спринта 26-28.11.2026 - это видно по истории коммитов.

Архитектурный шаблон скиллов (манифест `skill.yaml` + промпты + схемы + проверки кодом + тестовая модель `fake.py` +
тесты; классы данных `public/company/personal`; обезличивание ПДн в шлюзе до вызова модели) - внутренний стандарт
разработки MORE TECH, принятый до хакатона. В этом репозитории SDK скиллов (`sdk/`) и библиотека обезличивания
(`libs/pii_guard`) реализованы заново по этому стандарту; код из других репозиториев не копировался.

## Модели
| Модель | Лицензия | Карточка |
|---|---|---|
| Qwen3.6-35B-A3B | Apache 2.0 | https://huggingface.co/Qwen/Qwen3.6-35B-A3B |
| Qwen3.5-122B-A10B | Apache 2.0 | https://huggingface.co/Qwen/Qwen3.5-122B-A10B |
| BAAI/bge-m3 | MIT | https://huggingface.co/BAAI/bge-m3 |
| BAAI/bge-reranker-v2-m3 | Apache 2.0 | https://huggingface.co/BAAI/bge-reranker-v2-m3 |
| Natasha (NER для обезличивания) | MIT | https://github.com/natasha/natasha |

## Библиотеки
Python: FastAPI (MIT), Pydantic (MIT), SQLAlchemy (MIT), Alembic (MIT), psycopg (LGPL-3.0, динамическая связь),
pymorphy3 (MIT), rank-bm25 (Apache 2.0), RapidFuzz (MIT), sentence-transformers (Apache 2.0), PyTorch (BSD-3),
NumPy (BSD-3), python-docx (MIT), lxml (BSD-3), httpx (BSD-3), tenacity (Apache 2.0), imap-tools (Apache 2.0),
uvicorn (BSD-3), PyYAML (MIT).
Интерфейс: React (MIT), Vite (MIT), TypeScript (Apache 2.0).
Инфраструктура: PostgreSQL (PostgreSQL License), Caddy (Apache 2.0), vLLM (Apache 2.0).

## Внешние API
Облачное API модели (AI Tunnel - российский агрегатор, OpenAI-совместимый протокол) используется на стенде для
Qwen3.6-35B-A3B - это разрешено организаторами («можно использовать облачные API моделей, которые возможно
запускать локально»). Персональные данные маскируются до отправки.
