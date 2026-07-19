"""Ollama provider (local models via http://localhost:11434)."""
from __future__ import annotations

import json
from typing import Any, Sequence

import requests

from jarvis.providers.base import LLMProvider
from jarvis.types import GenerationResult, Message


class OllamaProvider(LLMProvider):
    name = "ollama"
    model = "llama3.1"

    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434", timeout: int = 120, **kwargs: Any) -> None:
        super().__init__(model=model, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        messages: Sequence[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Sequence[str] | None = None,
    ) -> GenerationResult:
        system, chat = self.split_roles(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": chat,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        if stop:
            payload["options"]["stop"] = list(stop)
        resp = requests.post(
            f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("message", {}).get("content", "")
        # Strip chain-of-thought blocks emitted by reasoning models (qwen3,
        # deepseek-r1, ...) so the orchestrator sees the final answer.
        text = self._strip_think(text)
        return GenerationResult(
            text=text,
            provider=self.name,
            model=self.model,
            usage=data.get("prompt_eval_count", 0),
        )

    @staticmethod
    def _strip_think(text: str) -> str:
        import re

        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

    def list_models(self) -> list[str]:
        """Enumerate locally installed Ollama models."""
        try:
            import requests

            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            return [m.get("name") for m in resp.json().get("models", [])]
        except Exception:
            return []
