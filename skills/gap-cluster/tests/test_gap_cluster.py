from gap_cluster import ClusterInput, GapCluster, GapQuestion
from skill_sdk import FakeLLM, SkillContext


def test_ids_deduplicated_and_leftovers_grouped() -> None:
    inp = ClusterInput(questions=[GapQuestion(id=str(i), text=f"вопрос {i}") for i in range(4)])
    llm = FakeLLM(
        {
            "gap-cluster/cluster": lambda _u: {
                "clusters": [
                    {"title": "A", "question_ids": ["0", "1", "1", "99"]},
                    {"title": "B", "question_ids": ["1", "2"]},
                ]
            }
        }
    )
    out = GapCluster().run(inp, SkillContext(llm=llm))
    assert [(c.title, c.question_ids) for c in out.clusters] == [("A", ["0", "1"]), ("B", ["2"]), ("Без темы", ["3"])]
