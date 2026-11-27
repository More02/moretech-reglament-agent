"""Эмбеддинги: BGE-M3 локально (sentence-transformers) или детерминированный хэш-векторизатор для тестов."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from ru_text import lemmas

log = logging.getLogger(__name__)
Vector = NDArray[np.float32]


class Embedder(Protocol):
    name: str

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Нормированные векторы, по строке на текст."""
        ...


class HashingEmbedder:
    """Мешок лемм и символьных триграмм в 1024 корзины. Без сети и модели - для тестов и запасного режима."""

    name = "hashing-1024"

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        lem = lemmas(text)
        grams = [w[i : i + 3] for w in lem for i in range(max(1, len(w) - 2))]
        return lem + grams

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for feat in self._features(text):
                h = int(hashlib.md5(feat.encode("utf-8"), usedforsecurity=False).hexdigest()[:8], 16)
                out[row, h % self.dim] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


class SentenceTransformerEmbedder:
    """BGE-M3 (MIT) на CPU сервера: тексты регламентов никуда не уходят."""

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self._model = SentenceTransformer(model_name, device=device)

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True, batch_size=16, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)


def make_embedder(backend: str, model_name: str, device: str) -> Embedder:
    if backend == "hashing":
        return HashingEmbedder()
    try:
        return SentenceTransformerEmbedder(model_name, device)
    except ImportError:
        if backend == "sentence-transformers":
            raise
        log.warning("sentence-transformers не установлен - работаю на хэш-эмбеддингах")
        return HashingEmbedder()


def to_bytes(vec: Vector) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def from_bytes(blob: bytes) -> Vector:
    return np.frombuffer(blob, dtype=np.float32)
