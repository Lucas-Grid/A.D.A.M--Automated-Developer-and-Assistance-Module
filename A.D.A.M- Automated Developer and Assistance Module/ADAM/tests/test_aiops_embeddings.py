"""Tests for aiops embeddings."""
import os

import pytest

from ADAM.aiops.embeddings import (
    OpenAICompatEmbeddingProvider,
    OllamaEmbeddingProvider,
)


class FakeEmbeddingProvider:
    """Deterministic fake provider for tests."""

    def __init__(self, dimension: int = 8) -> None:
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        return [0.1] * self._dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dimension for _ in texts]


def test_ollama_embedding_provider_instantiation():
    provider = OllamaEmbeddingProvider(base_url="http://localhost:11434", model="nomic-embed-text")
    assert provider._model == "nomic-embed-text"


def test_openai_compat_embedding_provider_instantiation():
    provider = OpenAICompatEmbeddingProvider(base_url="https://api.example.com", api_key="test", model="embed")
    assert provider._api_key == "test"


def test_fake_embedding_provider_returns_fixed_vector():
    provider = FakeEmbeddingProvider(dimension=4)
    import asyncio
    vector = asyncio.run(provider.embed("hello"))
    assert len(vector) == 4
    assert all(abs(v - 0.1) < 1e-6 for v in vector)
