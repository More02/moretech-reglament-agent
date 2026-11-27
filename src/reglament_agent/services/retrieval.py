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
    alias_of: str | None = None  # строка-перечисление длинного пункта: находится отдельно, отдаётся пункт целиком


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
        out: dict[str, list[Hit]] = {d: [] for d in departments}
        if not st.units or st.bm25 is None:
            return out
        fusion = self._fuse(st, [q for q in queries if q.strip()])
        taken: dict[str, set[str]] = {d: set() for d in departments}
        for idx, score in sorted(fusion.scores.items(), key=lambda kv: -kv[1]):
            unit = st.by_id.get(st.units[idx].alias_of or "", st.units[idx])
            if unit.kind != kind:
                continue
            boost = 1.15 if process and unit.process == process else 1.0
            hit = Hit(unit, score * boost, fusion.bm25.get(idx), fusion.dense.get(idx), float(fusion.dense_scores[idx]))
            for dep in departments if not unit.departments else [d for d in unit.departments if d in out]:
                if len(out[dep]) < per_department and unit.id not in taken[dep]:
                    taken[dep].add(unit.id)
                    out[dep].append(hit)
        for dep in out:
            out[dep].sort(key=lambda h: -h.score)
        return out

    def _fuse(self, st: _State, queries: list[str]) -> _Fusion:
        """Reciprocal Rank Fusion рейтингов BM25 и векторного поиска по всем переформулировкам запроса."""
        fusion = _Fusion(dense_scores=np.zeros(len(st.units), dtype=np.float32))
        if st.bm25 is None:
            return fusion
        for q in queries:
            bm = np.asarray(st.bm25.get_scores(self._tokens(q)), dtype=np.float32)
            qv = self.embedder.embed([self.glossary.expand(q)])[0]
            dn = st.vectors @ qv if st.vectors.shape[0] else np.zeros(len(st.units), dtype=np.float32)
            fusion.dense_scores = np.maximum(fusion.dense_scores, dn)
            for ranks, store in ((np.argsort(-bm), fusion.bm25), (np.argsort(-dn), fusion.dense)):
                for rank, idx in enumerate(ranks[:200]):
                    i = int(idx)
                    fusion.scores[i] += 1.0 / (RRF_K + rank + 1)
                    store[i] = min(store.get(i, rank), rank)
        return fusion


@dataclass
class _Fusion:
    dense_scores: NDArray[np.float32]
    scores: defaultdict[int, float] = field(default_factory=lambda: defaultdict(float))
    bm25: dict[int, int] = field(default_factory=dict)
    dense: dict[int, int] = field(default_factory=dict)
