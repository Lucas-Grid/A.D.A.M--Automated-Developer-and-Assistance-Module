"""Tests for aiops retrieval."""
import os

import pytest

from ADAM.aiops.retrieval import Retriever
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
def retriever(tmp_path):
    persist = str(tmp_path / "chroma")
    store = VectorStore(persist_directory=persist, collection_name="test")
    store.add(
        ids=["1", "2"],
        documents=["hello world", "goodbye world"],
        embeddings=[[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]],
        metadatas=[{"source": "test"}] * 2,
    )
    provider = FakeEmbeddingProvider(dimension=3)
    return Retriever(vector_store=store, embedding_provider=provider)


@pytest.mark.asyncio
async def test_retriever_returns_results(retriever):
    results = await retriever.search("hello", top_k=1)
    assert len(results) == 1
    assert "document" in results[0]
    assert "score" in results[0]
