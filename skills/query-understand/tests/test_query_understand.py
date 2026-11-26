from __future__ import annotations

from typing import Any

from query_understand import DepartmentRef, Intent, QueryUnderstand, UnderstandInput
from query_understand.fake import HANDLERS
from skill_sdk import FakeLLM, SkillContext

DEPTS = [
    DepartmentRef(id="dbrct", name="ДБРЦТ", aliases=["ДБР"]),
    DepartmentRef(id="ib", name="Дирекция ИБ", aliases=["ИБ"]),
]


def run(question: str, handler: Any = None) -> Any:
    llm = FakeLLM({"query-understand/understand": handler} if handler else HANDLERS)
    inp = UnderstandInput(
        question=question,
        departments=DEPTS,
        glossary_hits={"РП": "Руководитель проекта"},
        out_of_scope_topics=["премия"],
    )
    return QueryUnderstand().run(inp, SkillContext(llm=llm))


def test_regulation_question_with_department_and_glossary() -> None:
    out = run("Кто назначает РП в ИБ?")
    assert out.intent is Intent.REGULATION_QUESTION
    assert out.departments == ["ib"]
    assert out.search_queries == ["Кто назначает Руководитель проекта в ИБ?"]


def test_off_task_and_out_of_scope() -> None:
    assert run("Какой сегодня курс доллара?").intent is Intent.OFF_TASK
    out = run("Какую премию я получу за сделку?")
    assert out.intent is Intent.OUT_OF_SCOPE
    assert out.out_of_scope_topic == 0


def test_invented_department_and_topic_are_dropped() -> None:
    out = run(
        "вопрос",
        lambda _u: {
            "intent": "out_of_scope",
            "standalone_question": "",
            "search_queries": [],
            "departments": ["marketing", "ib", "ib"],
            "out_of_scope_topic": 7,
        },
    )
    assert out.departments == ["ib"]
    assert out.out_of_scope_topic == 0
    assert out.standalone_question == "вопрос"
    assert out.search_queries == ["вопрос"]


def test_two_departments_mean_complex_project() -> None:
    out = run("Что нужно для проекта ДБР и ИБ?")
    assert out.departments == ["dbrct", "ib"]
    assert out.complex_project
