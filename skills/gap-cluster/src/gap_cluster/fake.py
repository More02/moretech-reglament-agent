"""Тестовая модель группировки: по первому значимому слову вопроса."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ru_text import lemmas


def cluster(user: str) -> Mapping[str, Any]:
    data = json.loads(user.split("<data>", 1)[1].rsplit("</data>", 1)[0])
    groups: dict[str, list[str]] = {}
    for q in data["questions"]:
        key = next(iter(lemmas(q["text"])), "прочее")
        groups.setdefault(key, []).append(q["id"])
    return {"clusters": [{"title": k, "question_ids": v, "suggestion": ""} for k, v in groups.items()]}


HANDLERS = {"gap-cluster/cluster": cluster}
