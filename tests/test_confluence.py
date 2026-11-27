from __future__ import annotations

from pathlib import Path

import httpx

from reglament_agent.adapters.confluence import ConfluenceSource
from reglament_agent.passport import Passport

ROOT = Path(__file__).resolve().parents[1]
PAGE = (
    "<h1>Проектная деятельность ДБРЦТ</h1><p>1. Пресейл</p>"
    "<p>1.1. Заявка должна быть инициирована не менее чем за 3 рабочих дня до подачи предложения.</p>"
    "<ul><li>для точных оценок - 5 рабочих дней;</li></ul>"
)


def handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["Authorization"] == "Bearer t"
    assert request.url.params["spaceKey"] == "REG"
    return httpx.Response(
        200,
        json={
            "results": [
                {
                    "id": "101",
                    "title": "Проектная деятельность ДБРЦТ",
                    "version": {"number": 7},
                    "body": {"storage": {"value": PAGE}},
                }
            ],
            "size": 1,
            "limit": 50,
        },
    )


def test_confluence_pages_are_parsed_into_clauses() -> None:
    passport = Passport.load(ROOT / "passports" / "softline.yaml")
    source = ConfluenceSource("https://wiki.corp", "t", "REG", transport=httpx.MockTransport(handler))
    docs = source.documents(passport)
    assert len(docs) == 1
    meta, parsed = docs[0]
    assert meta.id == "dbrct-project"
    clause = parsed.clause("1.1")
    assert clause is not None
    assert "• для точных оценок - 5 рабочих дней;" in clause.text
