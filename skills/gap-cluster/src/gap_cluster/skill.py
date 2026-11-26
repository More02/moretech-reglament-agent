"""Группировка вопросов без ответа: модель группирует, код следит за идентификаторами и полнотой."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from gap_cluster.models import Cluster, ClusterInput, Clusters
from skill_sdk import Skill, SkillContext

SKILL_DIR = Path(__file__).resolve().parents[2]


class GapCluster(Skill[ClusterInput, Clusters]):
    skill_dir: ClassVar[Path] = SKILL_DIR

    def run(self, inp: ClusterInput, ctx: SkillContext) -> Clusters:
        if not inp.questions:
            return Clusters()
        raw = self.ask(ctx, "cluster", content=inp.model_dump(), output=Clusters)
        known = {q.id for q in inp.questions}
        used: set[str] = set()
        clusters: list[Cluster] = []
        for c in raw.clusters:
            ids = [i for i in dict.fromkeys(c.question_ids) if i in known and i not in used]
            if ids:
                used.update(ids)
                clusters.append(c.model_copy(update={"question_ids": ids}))
        rest = [q.id for q in inp.questions if q.id not in used]
        if rest:
            clusters.append(Cluster(title="Без темы", question_ids=rest, suggestion=""))
        clusters.sort(key=lambda c: len(c.question_ids), reverse=True)
        return Clusters(clusters=clusters)
