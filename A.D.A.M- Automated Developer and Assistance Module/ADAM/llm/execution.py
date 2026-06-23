"""LLM execution layer."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ProviderError
from ADAM.llm.failover import FailoverChain
from ADAM.llm.memory import LLMMemory
from ADAM.llm.router import LLMRouter
from ADAM.llm.telemetry import LLMTelemetry
from ADAM.llm.types import ChatMessage, LLMResponse

logger = logging.getLogger(__name__)


class LLMExecution:
    """Execute LLM calls through router + failover."""

    def __init__(self) -> None:
        self._router = LLMRouter()
        self._telemetry = LLMTelemetry()
        self._memory = LLMMemory()
        self._providers: list[Any] = []

    def set_providers(self, providers: list[Any]) -> None:
        self._providers = providers

    def chat(self, messages: list[ChatMessage], model_id: str | None = None, **kwargs: Any) -> LLMResponse:
        model = self._router.select(preferred_model=model_id)
        provider_name = model.get("provider", "unknown")
        provider = next((p for p in self._providers if getattr(p, "name", "") == provider_name), None)
        if provider is None:
            raise ProviderError(f"Provider '{provider_name}' not available")

        serialized = [{"role": m.role.value, "content": m.content} for m in messages]
        with self._telemetry.timer() as t:
            result = provider.chat(model=model["model_id"], messages=serialized, **kwargs)
        tokens = result.get("tokens_used", 0)
        self._telemetry.record_call(
            model=model["model_id"],
            provider=provider_name,
            latency_ms=getattr(t, "elapsed_ms", 0),
            tokens=tokens,
            success=True,
        )
        return LLMResponse(
            content=result.get("content", ""),
            model=model["model_id"],
            provider=provider_name,
            tokens_used=tokens,
            latency_ms=getattr(t, "elapsed_ms", 0),
            raw=result,
        )

    def stream(self, messages: list[ChatMessage], model_id: str | None = None, **kwargs: Any):
        model = self._router.select(preferred_model=model_id)
        provider_name = model.get("provider", "unknown")
        provider = next((p for p in self._providers if getattr(p, "name", "") == provider_name), None)
        if provider is None:
            raise ProviderError(f"Provider '{provider_name}' not available")
        if not hasattr(provider, "stream"):
            raise ProviderError(f"Provider '{provider_name}' does not support streaming")

        serialized = [{"role": m.role.value, "content": m.content} for m in messages]
        for chunk in provider.stream(model=model["model_id"], messages=serialized, **kwargs):
            yield chunk
