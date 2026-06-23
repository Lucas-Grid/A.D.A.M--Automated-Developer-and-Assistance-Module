"""Embedding providers for ADAM OS."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for a single text."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama embedding provider."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def embed(self, text: str) -> list[float]:
        vectors = await self.embed_batch([text])
        return vectors[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import httpx

        results: list[list[float]] = []
        async with httpx.AsyncClient() as client:
            for text in texts:
                resp = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                results.append(data.get("embedding", []))
        return results


class OpenAICompatEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI-compatible embedding provider."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        vectors = await self.embed_batch([text])
        return vectors[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import httpx

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {"model": self._model, "input": texts}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data.get("data", [])]


class OpenAIEmbeddingProvider(OpenAICompatEmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        super().__init__("https://api.openai.com/v1", api_key, model)


class NVIDIAEmbeddingProvider(OpenAICompatEmbeddingProvider):
    """NVIDIA NIM embedding provider."""

    def __init__(self, api_key: str, model: str = "nvidia/nv-embed-v1") -> None:
        super().__init__("https://integrate.api.nvidia.com/v1", api_key, model)


def get_embedding_provider(name: str, **kwargs: Any) -> BaseEmbeddingProvider:
    """Factory for embedding providers."""
    name = name.lower()
    if name == "ollama":
        return OllamaEmbeddingProvider(
            base_url=kwargs.get("base_url", "http://localhost:11434"),
            model=kwargs.get("model", "nomic-embed-text"),
        )
    if name == "openai":
        return OpenAIEmbeddingProvider(api_key=kwargs["api_key"], model=kwargs.get("model", "text-embedding-3-small"))
    if name in {"nvidia", "nvidia-nim"}:
        return NVIDIAEmbeddingProvider(api_key=kwargs["api_key"], model=kwargs.get("model", "nvidia/nv-embed-v1"))
    if name in {"openai-compat", "openrouter", "groq", "together", "mistral"}:
        return OpenAICompatEmbeddingProvider(
            base_url=kwargs["base_url"],
            api_key=kwargs["api_key"],
            model=kwargs["model"],
        )
    raise ValueError(f"Unsupported embedding provider: {name}")
