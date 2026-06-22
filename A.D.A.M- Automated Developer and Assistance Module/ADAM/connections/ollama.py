"""Ollama integration client stub."""
from __future__ import annotations

import logging
from typing import Any

import requests

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ConnectionError

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama local inference API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or get_settings().ollama_base_url).rstrip("/")

    def health(self) -> dict[str, Any]:
        """Check Ollama server health."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return {"ok": True, "models": response.json()}
        except Exception as exc:
            raise ConnectionError(f"Ollama is unreachable: {exc}") from exc

    def generate(self, model: str, prompt: str, *, stream: bool = False) -> dict[str, Any]:
        """Generate a completion."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ConnectionError(f"Ollama generation failed: {exc}") from exc
