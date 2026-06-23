"""Ollama provider implementation."""
from __future__ import annotations

import logging
import subprocess
from typing import Any

import requests

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ProviderError
from ADAM.connections.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    name = "ollama"
    display_name = "Ollama (Local)"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or get_settings().ollama_base_url).rstrip("/")

    def list_models(self) -> list[dict[str, Any]]:
        models = []
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            for m in data.get("models", []):
                models.append(
                    {
                        "model_id": m.get("name", "unknown"),
                        "provider": self.name,
                        "display_name": m.get("name", "unknown"),
                        "local_or_remote": "local",
                        "supports_chat": True,
                        "supports_vision": "vision" in m.get("details", {}).get("capabilities", []),
                        "supports_embeddings": False,
                        "supports_reasoning": False,
                        "context_window": m.get("context", {}).get("max_length", 0),
                        "availability_status": "available",
                    }
                )
        except Exception:
            # Fallback: ollama list CLI
            try:
                out = subprocess.check_output(["ollama", "list"], text=True, timeout=10)
                for line in out.strip().splitlines()[1:]:
                    parts = line.split()
                    if parts:
                        models.append(
                            {
                                "model_id": parts[0],
                                "provider": self.name,
                                "display_name": parts[0],
                                "local_or_remote": "local",
                                "supports_chat": True,
                                "supports_vision": False,
                                "supports_embeddings": False,
                                "supports_reasoning": False,
                                "context_window": 0,
                                "availability_status": "available",
                            }
                        )
            except Exception as exc:
                logger.warning("Ollama fallback list failed: %s", exc)
        return models

    def health(self) -> dict[str, Any]:
        try:
            requests.get(f"{self.base_url}/api/tags", timeout=3).raise_for_status()
            return {"provider": self.name, "status": "healthy"}
        except Exception as exc:
            return {"provider": self.name, "status": "unreachable", "error": str(exc)}

    def chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        payload = {"model": model, "messages": messages, "stream": False}
        try:
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ProviderError(f"Ollama chat failed: {exc}") from exc

    def embeddings(self, model: str, texts: list[str], **kwargs: Any) -> dict[str, Any]:
        raise ProviderError("Ollama embeddings not implemented in this provider")
