"""Provider abstraction layer for ADAM OS."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Common interface for all AI providers."""

    name: str = "base"
    display_name: str = "Base Provider"

    @abstractmethod
    def list_models(self) -> list[dict[str, Any]]:
        """Return available models with capabilities."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Check provider health/status."""

    @abstractmethod
    def chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Run a chat completion."""

    @abstractmethod
    def embeddings(self, model: str, texts: list[str], **kwargs: Any) -> dict[str, Any]:
        """Generate embeddings."""
