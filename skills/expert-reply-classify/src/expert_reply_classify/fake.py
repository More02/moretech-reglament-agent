"""Тестовая модель разбора письма."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def classify(user: str) -> Mapping[str, Any]:
    data = json.loads(user.split("<data>", 1)[1].rsplit("</data>", 1)[0])
    body: str = data["message"]["body"]
    low = body.lower()
    if "уточните" in low or "подскажите, какое" in low:
        return {"kind": "question_to_employee", "answer_text": "", "confidence": 0.8}
    if "подключаю" in low or "переадресую" in low:
        return {"kind": "forwarded_to_owner", "answer_text": "", "confidence": 0.8}
    if len(low) < 40:
        return {"kind": "acknowledgement", "answer_text": "", "confidence": 0.7}
    return {"kind": "final_answer", "answer_text": body.strip(), "confidence": 0.9}


HANDLERS = {"expert-reply-classify/classify": classify}
