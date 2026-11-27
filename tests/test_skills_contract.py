"""Контракт скиллов: манифест валиден, промпты на месте, тестовая модель знает все промпты скилла."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from skill_sdk import Manifest

SKILLS = sorted(p for p in (Path(__file__).resolve().parents[1] / "skills").iterdir() if (p / "skill.yaml").exists())


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda p: p.name)
def test_skill_contract(skill_dir: Path) -> None:
    manifest = Manifest.load(skill_dir)
    assert manifest.id == skill_dir.name
    module_name, class_name = manifest.entry.split(":")
    cls = getattr(importlib.import_module(module_name), class_name)
    assert cls.skill_dir == skill_dir
    source = (skill_dir / "src" / module_name.split(".")[0] / "skill.py").read_text(encoding="utf-8")
    prompts = set(re.findall(r'self\.ask\(\s*ctx,\s*"([a-z_]+)"', source))
    assert prompts, "скилл должен вызывать модель через self.ask"
    for name in prompts:
        text = (skill_dir / "prompts" / f"{name}.md").read_text(encoding="utf-8")
        assert "JSON" in text, f"промпт {name} должен требовать JSON"
    fake = importlib.import_module(f"{module_name.split('.')[0]}.fake")
    assert {f"{manifest.id}/{p}" for p in prompts} <= set(fake.HANDLERS)
    assert (skill_dir / "tests").is_dir()
