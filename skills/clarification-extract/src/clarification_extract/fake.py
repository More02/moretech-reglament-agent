"""Тестовая модель извлечения разъяснения."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


def extract(user: str) -> Mapping[str, Any]:
    data = json.loads(user.split("<data>", 1)[1].rsplit("</data>", 1)[0])
    answer = re.sub(r"^(добрый день|здравствуйте)[!,.]?\s*", "", data["expert_answer"].strip(), flags=re.IGNORECASE)
    first = re.split(r"(?<=[.!?])\s+", answer)[0]
    return {
        "canonical_question": data["question"].split("\n")[0],
        "answer": answer,
        "answer_quotes": [first],
        "department_ids": [data["employee_department"]] if data.get("employee_department") else [],
        "related_clause_ids": [c["id"] for c in data["candidate_clauses"][:1]],
        "keywords": [],
    }


HANDLERS = {"clarification-extract/extract": extract}
