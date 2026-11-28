from expert_reply_classify import ClassifyInput, ExpertReplyClassify, Message, ReplyKind, SenderRole
from expert_reply_classify.fake import HANDLERS
from skill_sdk import FakeLLM, SkillContext

ANSWER = "Добрый день! Такси в командировке в выходной день компенсируется по согласованию с руководителем проекта."


def run(body: str, role: SenderRole = SenderRole.QUALITY, llm: FakeLLM | None = None) -> object:
    inp = ClassifyInput(question="Такси в выходной?", message=Message(sender="q@corp.ru", body=body), sender_role=role)
    return ExpertReplyClassify().run(inp, SkillContext(llm=llm or FakeLLM(HANDLERS)))


def test_final_answer_from_quality() -> None:
    out = run(ANSWER)
    assert out.kind is ReplyKind.FINAL_ANSWER  # type: ignore[attr-defined]


def test_employee_cannot_answer_and_model_is_not_called() -> None:
    llm = FakeLLM({})
    out = run(ANSWER, SenderRole.EMPLOYEE, llm)
    assert out.kind is ReplyKind.OTHER  # type: ignore[attr-defined]
    assert llm.requests == []


def test_markers_override_model() -> None:
    assert run("#черновик " + ANSWER).kind is ReplyKind.OTHER  # type: ignore[attr-defined]
    out = run("Ок #ответ")
    assert out.kind is ReplyKind.FINAL_ANSWER  # type: ignore[attr-defined]
    assert out.answer_text == "Ок"  # type: ignore[attr-defined]


def test_invented_answer_text_is_replaced_by_mail_body() -> None:
    llm = FakeLLM(
        {
            "expert-reply-classify/classify": lambda _u: {
                "kind": "final_answer",
                "answer_text": "Такси никогда не компенсируется.",
            }
        }
    )
    out = run(ANSWER, llm=llm)
    assert out.answer_text == ANSWER  # type: ignore[attr-defined]


def test_markers_in_quoted_agent_letter_are_ignored() -> None:
    # Ответ из Яндекс-почты: под ответом эксперта - цитата письма агента с подсказкой про «#черновик».
    body = (
        "Такси компенсируется по согласованию с РП. #ответ\n\n----------------\n"
        "Кому: q@corp.ru\nТема: [РЕГ-0002] Вопрос\n"
        "Метка «#ответ» в письме - явный финальный ответ, «#черновик» - письмо не будет учтено."
    )
    out = run(body)
    assert out.kind is ReplyKind.FINAL_ANSWER  # type: ignore[attr-defined]
    assert "Кому" not in out.answer_text  # type: ignore[attr-defined]


def test_quote_without_line_breaks_is_cut() -> None:
    body = "Такси по согласованию с РП. #ответ      ----------------  Кому: q@corp.ru  «#черновик» - письмо не будет учтено."
    assert run(body).kind is ReplyKind.FINAL_ANSWER  # type: ignore[attr-defined]
