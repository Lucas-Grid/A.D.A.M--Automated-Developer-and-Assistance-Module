"""OpenAI-compatible provider helper."""
from __future__ import annotations

import logging
from typing import Any

import requests

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ProviderError

logger = logging.getLogger(__name__)


class OpenAICompatProvider:
    """Reusable implementation for OpenAI-compatible APIs."""

    def __init__(self, name: str, base_url: str, api_key: str) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}"
        resp = self._session.request(method, url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    def list_models(self) -> list[dict[str, Any]]:
        try:
            resp = self._request("GET", "/models")
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
                        "supports_vision": False,
                        "supports_embeddings": "embed" in mid.lower(),
                        "supports_reasoning": "reason" in mid.lower() or "o1" in mid.lower(),
                        "context_window": m.get("context_window", 0),
                        "availability_status": "available",
                    }
                )
            return models
        except Exception as exc:
            logger.warning("Failed to list models for %s: %s", self.name, exc)
            return []

    def health(self) -> dict[str, Any]:
        try:
            self._request("GET", "/models")
            return {"provider": self.name, "status": "healthy"}
        except Exception as exc:
            return {"provider": self.name, "status": "unreachable", "error": str(exc)}

    def chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        payload = {"model": model, "messages": messages, "stream": False}
        try:
            resp = self._request("POST", "/chat/completions", json=payload)
            return resp.json()
        except Exception as exc:
            raise ProviderError(f"{self.name} chat failed: {exc}") from exc

    def embeddings(self, model: str, texts: list[str], **kwargs: Any) -> dict[str, Any]:
        payload = {"model": model, "input": texts}
        try:
            resp = self._request("POST", "/embeddings", json=payload)
            return resp.json()
        except Exception as exc:
            raise ProviderError(f"{self.name} embeddings failed: {exc}") from exc
