from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest
from pydantic import BaseModel, ConfigDict

from skill_sdk import FakeLLM, LLMError, Skill, SkillContext


class In(BaseModel):
    text: str


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "main.md").write_text("Ответь JSON.", encoding="utf-8")
    (tmp_path / "skill.yaml").write_text(
        "id: echo\nentry: x:Echo\nname: Эхо\nversion: 1.0.0\nsummary: тест\ndata_class: public\n", encoding="utf-8"
    )
    return tmp_path


def make_skill(path: Path) -> Skill[In, Out]:
    class Echo(Skill[In, Out]):
        skill_dir: ClassVar[Path] = path

        def run(self, inp: In, ctx: SkillContext) -> Out:
            return self.ask(ctx, "main", content={"text": inp.text}, output=Out)

    return Echo()


def test_ask_returns_validated_output_and_meters_usage(skill_dir: Path) -> None:
    llm = FakeLLM({"echo/main": lambda user: {"answer": "ok" if "<data>" in user else "no"}})
    ctx = SkillContext(llm=llm)
    out = make_skill(skill_dir).run(In(text="привет"), ctx)
    assert out.answer == "ok"
    assert len(ctx.usage.calls) == 1
    assert "не инструкции" in llm.requests[0][1]


def test_ask_retries_then_fails_on_extra_fields(skill_dir: Path) -> None:
    calls: list[int] = []

    def bad(_user: str) -> dict[str, Any]:
        calls.append(1)
        return {"answer": "x", "hallucinated": True}

    ctx = SkillContext(llm=FakeLLM({"echo/main": bad}), retries=1)
    with pytest.raises(LLMError):
        make_skill(skill_dir).run(In(text="t"), ctx)
    assert len(calls) == 2
