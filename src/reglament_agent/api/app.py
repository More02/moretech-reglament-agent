"""Сборка FastAPI-приложения: роутеры, фоновый почтовый агент, статика интерфейса."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from reglament_agent.api import routes_admin, routes_channels, routes_chat, routes_documents, routes_mailbox
from reglament_agent.api.ratelimit import RateLimiter
from reglament_agent.config import ROOT, Settings, get_settings
from reglament_agent.container import Container, build_container

log = logging.getLogger(__name__)
WEB_DIST = ROOT / "web" / "dist"


async def mail_loop(container: Container) -> None:
    """Почтовый агент опрашивает ящик в фоне: ответы экспертов попадают в базу без участия людей."""
    while True:
        try:
            report = await asyncio.to_thread(container.mail.poll)
            if report.received:
                log.info(
                    "почта: писем %s, по обращениям %s, разъяснений %s",
                    report.received,
                    report.matched,
                    len(report.published_notes),
                )
        except Exception:
            log.exception("ошибка опроса почты")
        await asyncio.sleep(container.settings.mail_poll_seconds)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or build_container(settings)
        task = asyncio.create_task(mail_loop(app.state.container)) if settings.mail_poll_seconds > 0 else None
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="MORE TECH · Агент по регламентам", version="0.1.0", lifespan=lifespan)
    app.state.limiter = RateLimiter(settings.rate_limit_per_minute)
    for module in (routes_chat, routes_admin, routes_mailbox, routes_documents, routes_channels):
        app.include_router(module.router)
    if WEB_DIST.exists():
        _mount_web(app)
    return app


def _mount_web(app: FastAPI) -> None:
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        target = (WEB_DIST / path).resolve()
        if path and target.is_file() and WEB_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")
