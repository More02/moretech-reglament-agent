"""Записывает JSON-схемы входа и выхода каждого скилла в skills/<id>/schemas/ (для интеграций и ревью)."""

from __future__ import annotations

import importlib
import json
import typing
from pathlib import Path

from skill_sdk import Manifest

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for skill_dir in sorted((ROOT / "skills").iterdir()):
        if not (skill_dir / "skill.yaml").exists():
            continue
        manifest = Manifest.load(skill_dir)
        module_name, class_name = manifest.entry.split(":")
        cls = getattr(importlib.import_module(module_name), class_name)
        base = next(b for b in cls.__orig_bases__ if typing.get_origin(b) is not None)
        inp, out = typing.get_args(base)
        target = skill_dir / "schemas"
        target.mkdir(exist_ok=True)
        for name, model in (("input", inp), ("output", out)):
            schema = json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2)
            (target / f"{name}.json").write_text(schema + "\n", encoding="utf-8")
        print(f"{manifest.id}: {inp.__name__} → {out.__name__}")


if __name__ == "__main__":
    main()
