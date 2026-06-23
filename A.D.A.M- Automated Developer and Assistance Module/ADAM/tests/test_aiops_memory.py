"""Tests for aiops memory integration."""
import os

import pytest

from ADAM.aiops.memory_index import MemoryIndexer
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
def indexer(tmp_path):
    persist = str(tmp_path / "chroma")
    store = VectorStore(persist_directory=persist, collection_name="test")
    provider = FakeEmbeddingProvider(dimension=4)
    return MemoryIndexer(vector_store=store, embedding_provider=provider)


@pytest.mark.asyncio
async def test_reindex_all_returns_counts(indexer):
    result = await indexer.reindex_all()
    assert "memory" in result
    assert "knowledge" in result
    assert "automation" in result
    assert isinstance(result["memory"], int)
    assert isinstance(result["knowledge"], int)
    assert isinstance(result["automation"], int)
