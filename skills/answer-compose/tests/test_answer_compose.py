from __future__ import annotations

from typing import Any

from answer_compose import (
    AnswerCompose,
    ComposeInput,
    DepartmentSources,
    ExpertNote,
    Source,
    Status,
)
from answer_compose.fake import HANDLERS
from skill_sdk import FakeLLM, SkillContext

DBRCT = DepartmentSources(
    id="dbrct",
    name="ДБРЦТ",
    sources=[
        Source(
            id="dbrct-project:2.4",
            ref="п. 2.4, Проектная деятельность ДБРЦТ",
            text="Бюджетная оценка не может использоваться для подачи в конкурс (за исключением RFI), контрактования "
            "и определения начальной максимальной цены, т.к. данный расчёт не считается окончательным.",
        )
    ],
)
TECH = DepartmentSources(
    id="tech",
    name="Техническая дирекция",
    sources=[
        Source(
            id="tech-project:2.4",
            ref="п. 2.4, Организация проектной деятельности Технической дирекции",
            text="Важно! Бюджетная оценка не может использоваться для подачи в конкурс, контрактования и определения "
            "начальной максимальной цены (НМЦ), т.к. данный расчёт не считается окончательным.",
        )
    ],
)
INP = ComposeInput(question="Можно ли подать бюджетную оценку в конкурс?", departments=[DBRCT, TECH])


def run(handler: Any, inp: ComposeInput = INP) -> Any:
    return AnswerCompose().run(inp, SkillContext(llm=FakeLLM({"answer-compose/compose": handler})))


def model_answer(**overrides: Any) -> Any:
    base: dict[str, Any] = {
        "variants": [
            {
                "department_id": "dbrct",
                "status": "answered",
                "lead": "Нет, за исключением RFI.",
                "claims": [
                    {
                        "text": "Бюджетную оценку нельзя подавать в конкурс, кроме запроса RFI.",
                        "source_id": "dbrct-project:2.4",
                        "quote": "Бюджетная оценка не может использоваться для подачи в конкурс (за исключением RFI)",
                    }
                ],
            },
            {
                "department_id": "tech",
                "status": "answered",
                "lead": "Нет.",
                "claims": [
                    {
                        "text": "Бюджетную оценку нельзя подавать в конкурс.",
                        "source_id": "tech-project:2.4",
                        "quote": "Бюджетная оценка не может использоваться для подачи в конкурс",
                    }
                ],
            },
        ],
        "same_across_departments": False,
    }
    base.update(overrides)
    return lambda _u: base


def test_supported_claims_pass() -> None:
    out = run(model_answer())
    assert [v.status for v in out.variants] == [Status.ANSWERED, Status.ANSWERED]
    assert out.rejected == []


def test_claim_with_invented_quote_is_dropped_and_variant_becomes_not_found() -> None:
    bad = model_answer()(None)
    bad["variants"][1]["claims"][0]["quote"] = "Бюджетную оценку можно подать в конкурс при согласовании директора"
    out = run(lambda _u: bad)
    assert out.variants[1].status is Status.NOT_FOUND
    assert len(out.rejected) == 1


def test_claim_with_source_of_other_department_is_dropped() -> None:
    bad = model_answer()(None)
    bad["variants"][1]["claims"][0]["source_id"] = "dbrct-project:2.4"
    out = run(lambda _u: bad)
    assert out.variants[1].status is Status.NOT_FOUND
    assert "источник не из найденных" in out.rejected[0].reason


def test_wrong_number_in_claim_is_dropped() -> None:
    bad = model_answer()(None)
    bad["variants"][0]["claims"][0]["text"] = "Можно, если до подачи больше 5 дней."
    out = run(lambda _u: bad)
    assert out.variants[0].status is Status.NOT_FOUND


def test_missing_variant_is_added_as_not_found() -> None:
    partial = model_answer()(None)
    partial["variants"] = partial["variants"][:1]
    out = run(lambda _u: partial)
    assert [v.department_id for v in out.variants] == ["dbrct", "tech"]
    assert out.variants[1].status is Status.NOT_FOUND


def test_same_across_departments_is_rechecked_by_numbers() -> None:
    a = Source(id="a:1", ref="a", text="Руководитель проекта назначается в течение 1 рабочего дня после запроса.")
    b = Source(
        id="b:1", ref="b", text="Руководитель проекта назначается не позднее 12 рабочих часов с момента запроса."
    )
    inp = ComposeInput(
        question="Срок назначения РП?",
        departments=[
            DepartmentSources(id="a", name="A", sources=[a]),
            DepartmentSources(id="b", name="B", sources=[b]),
        ],
    )
    answer = {
        "variants": [
            {
                "department_id": "a",
                "status": "answered",
                "claims": [
                    {
                        "text": "РП назначают за 1 рабочий день.",
                        "source_id": "a:1",
                        "quote": "назначается в течение 1 рабочего дня после запроса",
                    }
                ],
            },
            {
                "department_id": "b",
                "status": "answered",
                "claims": [
                    {
                        "text": "РП назначают не позднее 12 рабочих часов.",
                        "source_id": "b:1",
                        "quote": "назначается не позднее 12 рабочих часов с момента запроса",
                    }
                ],
            },
        ],
        "same_across_departments": True,
    }
    out = run(lambda _u: answer, inp)
    assert out.same_across_departments is False


def test_expert_note_is_a_valid_source() -> None:
    note = ExpertNote(
        id="note:1",
        question="Компенсируется ли такси в командировке в выходной?",
        answer="Да, такси в выходной день в командировке компенсируется при согласовании руководителя проекта.",
    )
    inp = ComposeInput(question="такси в выходной в командировке", departments=[DBRCT], expert_notes=[note])
    out = AnswerCompose().run(inp, SkillContext(llm=FakeLLM(HANDLERS)))
    assert out.variants[0].claims[0].source_id == "note:1"


def test_no_sources_means_no_model_call() -> None:
    llm = FakeLLM({})
    inp = ComposeInput(question="?", departments=[DepartmentSources(id="x", name="X", sources=[])])
    out = AnswerCompose().run(inp, SkillContext(llm=llm))
    assert llm.requests == []
    assert out.variants[0].status is Status.NOT_FOUND


SUB = DepartmentSources(
    id="ib",
    name="ИБ",
    sources=[
        Source(
            id="ib-project:4.1",
            ref="п. 4.1",
            text="РП может привлечь субподрядчика к выполнению работ только после подписания субподрядного договора "
            "и при наличии Заказа покупателя в учётной системе, по которому пришла оплата или согласована КИ.",
        )
    ],
)
HALF = "РП может привлечь субподрядчика к выполнению работ только после подписания субподрядного договора"


def _half_rule(user: str) -> dict[str, Any]:
    del user
    claim = {"text": "Субподрядчика можно привлечь после подписания договора.", "source_id": "ib-project:4.1"}
    return {
        "variants": [{"department_id": "ib", "status": "answered", "claims": [{**claim, "quote": HALF}]}],
        "same_across_departments": False,
        "conflict": None,
        "missing_documents": [],
    }


def test_lost_condition_asks_model_again_with_feedback() -> None:
    llm = FakeLLM({"answer-compose/compose": _half_rule})
    inp = ComposeInput(question="Когда можно подключать субподрядчика?", departments=[SUB])
    out = AnswerCompose().run(inp, SkillContext(llm=llm))
    assert len(llm.requests) == 2
    assert "Заказа покупателя" in llm.requests[1][1]
    # Модель не исправилась - утверждением становится предложение регламента целиком.
    claim = out.variants[0].claims[0]
    assert "Заказа покупателя" in claim.text
    assert claim.quote == claim.text
