from answer_verify import AnswerVerify, ClaimToCheck, Verdict, VerifyInput
from answer_verify.fake import HANDLERS
from skill_sdk import FakeLLM, SkillContext

SRC = "Работы со стороны команды проекта без подписанного договора и согласованной сметы запрещены."


def test_fake_verifier_flags_unsupported_claim() -> None:
    inp = VerifyInput(
        question="можно без договора?",
        claims=[
            ClaimToCheck(id="c1", text="Без подписанного договора и сметы работы запрещены.", source_text=SRC),
            ClaimToCheck(id="c2", text="Можно начать, если клиент устно пообещал оплату.", source_text=SRC),
        ],
    )
    out = AnswerVerify().run(inp, SkillContext(llm=FakeLLM(HANDLERS)))
    assert [v.verdict for v in out.verdicts] == [Verdict.SUPPORTED, Verdict.UNSUPPORTED]
    assert out.failed_ids() == {"c2"}


def test_missing_and_invented_verdicts() -> None:
    inp = VerifyInput(question="?", claims=[ClaimToCheck(id="c1", text="t", source_text=SRC)])
    llm = FakeLLM({"answer-verify/verify": lambda _u: {"verdicts": [{"id": "zzz", "verdict": "supported"}]}})
    out = AnswerVerify().run(inp, SkillContext(llm=llm))
    assert out.failed_ids() == {"c1"}
