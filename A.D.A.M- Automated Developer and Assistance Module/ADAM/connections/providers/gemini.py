"""Gemini provider."""
from __future__ import annotations

import logging
from typing import Any

import requests

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ProviderError
from ADAM.connections.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    name = "gemini"
    display_name = "Google Gemini"

    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.gemini_base_url.rstrip("/")
        self.api_key = s.gemini_api_key

    def list_models(self) -> list[dict[str, Any]]:
        try:
            resp = requests.get(f"{self.base_url}/models?key={self.api_key}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                mid = m.get("name", "unknown").split("/")[-1]
                models.append(
                    {
                        "model_id": mid,
                        "provider": self.name,
                        "display_name": m.get("displayName", mid),
                        "local_or_remote": "remote",
                        "supports_chat": True,
                        "supports_vision": "image" in m.get("supportedGenerationMethods", []),
                        "supports_embeddings": "embed" in m.get("supportedGenerationMethods", []),
                        "supports_reasoning": False,
                        "context_window": m.get("inputTokenLimit", 0),
                        "availability_status": "available",
                    }
                )
            return models
        except Exception as exc:
            logger.warning("Gemini list_models failed: %s", exc)
            return []

    def health(self) -> dict[str, Any]:
        try:
            requests.get(f"{self.base_url}/models?key={self.api_key}", timeout=5).raise_for_status()
            return {"provider": self.name, "status": "healthy"}
        except Exception as exc:
            return {"provider": self.name, "status": "unreachable", "error": str(exc)}

    def chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        # Convert OpenAI-style messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        payload = {"contents": contents}
        try:
            resp = requests.post(
                f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise ProviderError(f"Gemini chat failed: {exc}") from exc

    def embeddings(self, model: str, texts: list[str], **kwargs: Any) -> dict[str, Any]:
        payload = {"requests": [{"model": model, "text": t} for t in texts]}
        try:
            resp = requests.post(
                f"{self.base_url}/models/{model}:batchEmbedTexts?key={self.api_key}",
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise ProviderError(f"Gemini embeddings failed: {exc}") from exc
