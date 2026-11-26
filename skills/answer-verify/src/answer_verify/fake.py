"""Тестовая модель проверяющего: утверждение подтверждено, если большая часть его лемм есть в источнике."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ru_text import lemmas

_SHARE = 0.6


def verify(user: str) -> Mapping[str, Any]:
    data = json.loads(user.split("<data>", 1)[1].rsplit("</data>", 1)[0])
    out = []
    for c in data["claims"]:
        claim, source = set(lemmas(c["text"])), set(lemmas(c["source_text"]))
        ok = bool(claim) and len(claim & source) / len(claim) >= _SHARE
        out.append(
            {"id": c["id"], "verdict": "supported" if ok else "unsupported", "comment": "" if ok else "нет в источнике"}
        )
    return {"verdicts": out}


HANDLERS = {"answer-verify/verify": verify}
