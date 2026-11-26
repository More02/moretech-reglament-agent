"""Тестовая модель ответа: берёт пункт с наибольшим пересечением лемм с вопросом и цитирует первое предложение."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from ru_text import lemmas

_MIN_OVERLAP = 2


def _first_sentence(text: str) -> str:
    first = re.split(r"(?<=[.;:])\s+|\n", text.strip())[0]
    return first if len(first) >= 20 else text.strip().split("\n")[0]


def compose(user: str) -> Mapping[str, Any]:
    data = json.loads(user.split("<data>", 1)[1].rsplit("</data>", 1)[0])
    q = set(lemmas(data["question"]))
    variants = []
    for dep in data["departments"]:
        pool = [*dep["sources"]]
        pool += [
            {"id": n["id"], "text": n["answer"]}
            for n in data.get("expert_notes", [])
            if not n["department_ids"] or dep["id"] in n["department_ids"]
        ]
        scored = sorted(pool, key=lambda s: len(q & set(lemmas(s["text"]))), reverse=True)
        best = scored[0] if scored else None
        if best is None or len(q & set(lemmas(best["text"]))) < _MIN_OVERLAP:
            variants.append({"department_id": dep["id"], "status": "not_found", "gap": "нет в источниках"})
            continue
        sentence = _first_sentence(best["text"])
        variants.append(
            {
                "department_id": dep["id"],
                "status": "answered",
                "lead": "",
                "claims": [{"text": sentence, "source_id": best["id"], "quote": sentence}],
            }
        )
    return {"variants": variants, "same_across_departments": False, "conflict": None, "missing_documents": []}


HANDLERS = {"answer-compose/compose": compose}
