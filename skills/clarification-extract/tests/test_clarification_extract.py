from clarification_extract import CandidateClause, ClarificationExtract, ExtractInput
from skill_sdk import FakeLLM, SkillContext

INP = ExtractInput(
    question="Компенсируют ли такси в командировке в выходной?",
    expert_answer="Добрый день! Да, такси в выходной день компенсируется при согласовании руководителя проекта.",
    departments={"dbrct": "ДБРЦТ"},
    employee_department="dbrct",
    candidate_clauses=[CandidateClause(id="dbrct-project:3.8", ref="п. 3.8", text="...")],
)


def test_invented_ids_and_quotes_are_dropped() -> None:
    llm = FakeLLM(
        {
            "clarification-extract/extract": lambda _u: {
                "canonical_question": "Компенсируется ли такси в командировке в выходной день?",
                "answer": "Такси компенсируется всегда.",
                "answer_quotes": ["такси компенсируется всегда без согласования"],
                "department_ids": ["dbrct", "hr"],
                "related_clause_ids": ["dbrct-project:3.8", "x:1"],
                "keywords": ["такси", "командировка"],
            }
        }
    )
    out = ClarificationExtract().run(INP, SkillContext(llm=llm))
    assert out.answer == INP.expert_answer  # пересказ без опоры заменён словами эксперта
    assert out.department_ids == ["dbrct"]
    assert out.related_clause_ids == ["dbrct-project:3.8"]
