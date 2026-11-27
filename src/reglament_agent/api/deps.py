"""Зависимости роутеров: контейнер приложения, ограничение частоты, доступ к кабинету."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from reglament_agent.container import Container


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def rate_limited(request: Request) -> None:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")
    if not request.app.state.limiter.allow(ip):
        raise HTTPException(429, "Слишком много запросов. Подождите минуту.")


def admin_only(request: Request, x_admin_token: Annotated[str | None, Header()] = None) -> None:
    token = request.app.state.container.settings.admin_token
    if token and x_admin_token != token:
        raise HTTPException(401, "Нужен токен кабинета службы качества")
