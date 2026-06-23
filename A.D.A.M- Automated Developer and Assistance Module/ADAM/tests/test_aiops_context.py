"""Tests for aiops context builder."""
import asyncio
import os

import pytest

from ADAM.aiops.context_builder import ContextBuilder
from ADAM.aiops.embeddings import OllamaEmbeddingProvider
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
def builder(tmp_path):
    persist = str(tmp_path / "chroma")
    store = VectorStore(persist_directory=persist, collection_name="test")
    provider = FakeEmbeddingProvider(dimension=3)
    retriever = Retriever(vector_store=store, embedding_provider=provider)
    return ContextBuilder(retriever=retriever)


def test_context_builder_returns_package(builder):
    package = asyncio.run(builder.build("test query"))
    assert "query" in package
    assert "memory_context" in package
    assert "graph_context" in package
    assert "automation_context" in package
    assert "vector_context" in package
