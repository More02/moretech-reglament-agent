"""Командная строка: загрузка регламентов, сервер, почта, садовник, тестовый прогон."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict

from reglament_agent.config import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reglament", description="Агент ответов по регламентам MORE TECH")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ingest = sub.add_parser("ingest", help="Загрузить регламенты из REGULATIONS_DIR и пересобрать индекс")
    ingest.add_argument(
        "--exit", action="store_true", help="Завершить процесс сразу после отчёта (фоновые потоки загрузчика модели)"
    )
    serve = sub.add_parser("serve", help="Запустить HTTP API и интерфейс")
    serve.add_argument("--host", default="0.0.0.0")  # noqa: S104 - сервер в контейнере
    serve.add_argument("--port", type=int, default=8000)
    sub.add_parser("mail-poll", help="Один раз проверить почту агента")
    garden = sub.add_parser("gardener", help="Пробелы в регламентах и разъяснения на перепроверку")
    garden.add_argument("--send-digest", action="store_true")
    ev = sub.add_parser("eval", help="Прогон тестового набора вопросов")
    ev.add_argument("--fake", action="store_true", help="Тестовая модель (без сети)")
    ev.add_argument("--limit", type=int, default=0)
    ev.add_argument("--fail-under", type=float, default=0.0)
    ev.add_argument("--judge", action="store_true", help="Проверять ответы второй моделью")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    if args.cmd == "serve":
        import uvicorn

        from reglament_agent.api.app import create_app

        uvicorn.run(create_app(settings), host=args.host, port=args.port, proxy_headers=True)
        return 0

    from reglament_agent.container import build_container

    if args.cmd == "eval":
        from reglament_agent.evals import run_eval

        settings = settings.model_copy(update={"llm_fake": args.fake or settings.llm_fake})
        score = run_eval(settings, limit=args.limit, judge=args.judge)
        return 0 if score >= args.fail_under else 1

    container = build_container(settings)
    if args.cmd == "ingest":
        if settings.confluence_url:
            from reglament_agent.adapters.confluence import ConfluenceSource

            source = ConfluenceSource(settings.confluence_url, settings.confluence_token, settings.confluence_space)
            documents = source.documents(container.passport)
        else:
            documents = container.kb.parse_directory(settings.regulations_dir)
        report = container.kb.ingest(documents)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=1), flush=True)
        if args.exit:
            # При запуске контейнера: фоновые потоки загрузчика модели эмбеддингов не дают процессу завершиться,
            # а сервер стартует только после загрузки регламентов. Работа сделана и записана в базу.
            os._exit(0)
    elif args.cmd == "mail-poll":
        print(container.mail.poll())
    elif args.cmd == "gardener":
        r = container.gardener.run(send_digest=args.send_digest)
        print(json.dumps([c.model_dump() for c in r.clusters], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
