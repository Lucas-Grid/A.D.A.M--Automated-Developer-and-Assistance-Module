"""Anthropic provider."""
from __future__ import annotations

import logging
from typing import Any

import requests

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ProviderError
from ADAM.connections.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    display_name = "Anthropic Claude"

    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.anthropic_base_url.rstrip("/")
        self.api_key = s.anthropic_api_key
        self._session = requests.Session()
        self._session.headers.update({"x-api-key": self.api_key, "anthropic-version": "2023-06-01"})

    def list_models(self) -> list[dict[str, Any]]:
        try:
            resp = self._session.get(f"{self.base_url}/v1/models", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "unknown")
                models.append(
                    {
                        "model_id": mid,
                        "provider": self.name,
                        "display_name": mid,
                        "local_or_remote": "remote",
                        "supports_chat": True,
                        "supports_vision": "vision" in mid.lower(),
                        "supports_embeddings": False,
                        "supports_reasoning": "reason" in mid.lower() or "claude-3" in mid.lower(),
                        "context_window": m.get("context_window", 0),
                        "availability_status": "available",
                    }
                )
            return models
        except Exception as exc:
            logger.warning("Anthropic list_models failed: %s", exc)
            return []

    def health(self) -> dict[str, Any]:
        try:
            self._session.get(f"{self.base_url}/v1/models", timeout=5).raise_for_status()
            return {"provider": self.name, "status": "healthy"}
        except Exception as exc:
            return {"provider": self.name, "status": "unreachable", "error": str(exc)}

    def chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "messages": messages,
        }
        try:
            resp = self._session.post(f"{self.base_url}/v1/messages", json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise ProviderError(f"Anthropic chat failed: {exc}") from exc

    def embeddings(self, model: str, texts: list[str], **kwargs: Any) -> dict[str, Any]:
        raise ProviderError("Anthropic embeddings not supported")
