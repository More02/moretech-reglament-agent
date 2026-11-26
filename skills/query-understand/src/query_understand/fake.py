"""Тестовая модель для скилла: простые правила вместо LLM, чтобы тесты и эвалы шли без сети."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

_OFF_TASK = ("курс доллара", "follow-up", "фоллоу", "переведи", "напиши письмо", "погода")
_OUT_OF_SCOPE = ("премию", "премия", "зарплат", "маржа по моей", "маржу по моей", "отпуск")
_GREETING = ("привет", "спасибо", "что ты умеешь", "добрый день")
_FIND_DOC = ("найди регламент", "где регламент", "дай ссылку на регламент", "покажи регламент")


def _payload(user: str) -> dict[str, Any]:
    body = user.split("<data>", 1)[1].rsplit("</data>", 1)[0]
    data: dict[str, Any] = json.loads(body)
    return data


def understand(user: str) -> Mapping[str, Any]:
    data = _payload(user)
    q: str = data["question"]
    low = q.lower()
    intent = "regulation_question"
    if any(k in low for k in _OFF_TASK):
        intent = "off_task"
    elif any(k in low for k in _OUT_OF_SCOPE):
        intent = "out_of_scope"
    elif any(low.startswith(k) for k in _GREETING):
        intent = "greeting"
    elif any(k in low for k in _FIND_DOC):
        intent = "find_document"
    departments = [
        d["id"]
        for d in data["departments"]
        if any(re.search(rf"(?<!\w){re.escape(a.lower())}(?!\w)", low) for a in [d["name"], *d["aliases"]])
    ]
    query = q
    for abbr, term in data.get("glossary_hits", {}).items():
        query = query.replace(abbr, term)
    return {
        "intent": intent,
        "standalone_question": q,
        "search_queries": [query],
        "departments": departments,
        "complex_project": "комплексн" in low,
        "process": "presale" if "пресейл" in low else None,
        "out_of_scope_topic": 0 if intent == "out_of_scope" else None,
    }


HANDLERS = {"query-understand/understand": understand}
