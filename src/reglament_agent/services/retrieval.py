"""Гибридный поиск по пунктам регламентов и разъяснениям: BM25 по леммам + векторы, RRF, квоты по подразделениям.

Почему квоты: обычный top-k по всей базе отдаёт места пунктам самого объёмного документа, и агент «не видит», что в
другом подразделении правило другое. Каждое подходящее подразделение получает свои лучшие пункты.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from rank_bm25 import BM25Okapi

from reglament_agent.adapters.embeddings import Embedder
from ru_text import Glossary, lemmas

RRF_K = 60
SHORT_SECTION_CHARS = 220
MAX_CHILDREN = 6


@dataclass(frozen=True, slots=True)
class Unit:
    """Единица поиска: пункт регламента или разъяснение службы качества."""

    id: str
    kind: str  # clause | note
    departments: tuple[str, ...]  # пусто - для всех подразделений
    process: str | None
    title: str
    text: str
    search_text: str
    parent: str | None = None
    doc_id: str | None = None
    number: str | None = None


@dataclass(frozen=True, slots=True)
class Hit:
    unit: Unit
    score: float
    bm25_rank: int | None
    dense_rank: int | None
    dense_score: float


@dataclass
class _State:
    units: list[Unit] = field(default_factory=list)
    vectors: NDArray[np.float32] = field(default_factory=lambda: np.zeros((0, 1), dtype=np.float32))
    bm25: BM25Okapi | None = None
    children: dict[str, list[str]] = field(default_factory=dict)
    by_id: dict[str, Unit] = field(default_factory=dict)


class HybridIndex:
    """Индекс в памяти процесса. Пересобирается целиком при загрузке регламентов и разъяснений (атомарно).

    Для корпуса до десятков тысяч пунктов это быстрее и проще отдельного векторного хранилища; при росте порт
    заменяется на pgvector или Qdrant без изменения агента (см. docs/adr/0002-search.md).
    """

    def __init__(self, embedder: Embedder, glossary: Glossary) -> None:
        self.embedder = embedder
        self.glossary = glossary
        self._state = _State()
        self._lock = threading.Lock()

    def rebuild(self, units: Sequence[Unit], vectors: NDArray[np.float32] | None = None) -> None:
        units = list(units)
        if vectors is None:
            vectors = self.embedder.embed([u.search_text for u in units]) if units else None
        tokenized = [self._tokens(u.search_text) or ["_"] for u in units]
        children: dict[str, list[str]] = defaultdict(list)
        for u in units:
            if u.kind == "clause" and u.parent and u.doc_id:
                children[f"{u.doc_id}:{u.parent}"].append(u.id)
        state = _State(
            units=units,
            vectors=vectors if vectors is not None else np.zeros((0, 1), dtype=np.float32),
            bm25=BM25Okapi(tokenized) if units else None,
            children=dict(children),
            by_id={u.id: u for u in units},
        )
        with self._lock:
            self._state = state

    def _tokens(self, text: str) -> list[str]:
        return lemmas(self.glossary.expand(text))

    def unit(self, unit_id: str) -> Unit | None:
        return self._state.by_id.get(unit_id)

    def children_of(self, unit: Unit) -> list[Unit]:
        st = self._state
        return [st.by_id[c] for c in st.children.get(unit.id, [])]

    def search(
        self,
        queries: Iterable[str],
        *,
        departments: Sequence[str],
        per_department: int = 6,
        kind: str = "clause",
        process: str | None = None,
    ) -> dict[str, list[Hit]]:
        """Лучшие единицы для каждого подразделения из ``departments``. Стадия процесса - мягкий приоритет."""
        st = self._state
        if not st.units or st.bm25 is None:
            return {d: [] for d in departments}
        queries = [q for q in queries if q.strip()]
        fused: dict[int, float] = defaultdict(float)
        best_bm25: dict[int, int] = {}
        best_dense: dict[int, int] = {}
        dense_scores = np.zeros(len(st.units), dtype=np.float32)
        for q in queries:
            bm = np.asarray(st.bm25.get_scores(self._tokens(q)), dtype=np.float32)
            qv = self.embedder.embed([self.glossary.expand(q)])[0]
            dn = st.vectors @ qv if st.vectors.shape[0] else np.zeros(len(st.units), dtype=np.float32)
            dense_scores = np.maximum(dense_scores, dn)
            for ranks, store in ((np.argsort(-bm), best_bm25), (np.argsort(-dn), best_dense)):
                for rank, idx in enumerate(ranks[:200]):
                    i = int(idx)
                    fused[i] += 1.0 / (RRF_K + rank + 1)
                    store[i] = min(store.get(i, rank), rank)
        out: dict[str, list[Hit]] = {d: [] for d in departments}
        for idx, score in sorted(fused.items(), key=lambda kv: -kv[1]):
            unit = st.units[idx]
            if unit.kind != kind:
                continue
            boost = 1.15 if process and unit.process == process else 1.0
            targets = departments if not unit.departments else [d for d in unit.departments if d in out]
            for dep in targets:
                if len(out[dep]) < per_department:
                    out[dep].append(
                        Hit(unit, score * boost, best_bm25.get(idx), best_dense.get(idx), float(dense_scores[idx]))
                    )
        for dep in out:
            out[dep].sort(key=lambda h: -h.score)
        return out
