"""Tests for aiops vector store."""
import os

import pytest

from ADAM.aiops.vector_store import VectorStore


class FakeEmbeddingProvider:
    """Deterministic fake provider for tests."""

    def __init__(self, dimension: int = 8) -> None:
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        return [0.1] * self._dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dimension for _ in texts]


@pytest.fixture()
def vector_store(tmp_path):
    persist = str(tmp_path / "chroma")
    return VectorStore(persist_directory=persist, collection_name="test")


def test_vector_store_add_and_count(vector_store):
    assert vector_store.count() == 0
    vector_store.add(
        ids=["1"],
        documents=["hello world"],
        embeddings=[[0.1, 0.2, 0.3]],
        metadatas=[{"source": "test"}],
    )
    assert vector_store.count() == 1


def test_vector_store_search(vector_store):
    vector_store.add(
        ids=["1", "2"],
        documents=["hello world", "goodbye world"],
        embeddings=[[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]],
        metadatas=[{"source": "test"}] * 2,
    )
    results = vector_store.search([0.1, 0.2, 0.3], top_k=2)
    assert len(results["ids"]) == 2
    assert results["ids"][0] == "1"
