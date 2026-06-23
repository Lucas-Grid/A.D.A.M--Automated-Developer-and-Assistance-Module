"""LLM failover system."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.core.exceptions import ModelRegistryError, ProviderError
from ADAM.llm.telemetry import LLMTelemetry

logger = logging.getLogger(__name__)


class FailoverChain:
    """Try providers in order until one succeeds."""

    def __init__(self, providers: list[Any], telemetry: LLMTelemetry | None = None) -> None:
        self._providers = providers
        self._telemetry = telemetry or LLMTelemetry()

    def execute(self, method: str, *args: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                func = getattr(provider, method)
                with self._telemetry._Timer() as t:
                    result = func(*args, **kwargs)
                self._telemetry.record_call(
                    model=kwargs.get("model", "unknown"),
                    provider=provider.name,
                    latency_ms=getattr(t, "elapsed_ms", 0),
                    tokens=result.get("tokens_used", 0) if isinstance(result, dict) else 0,
                    success=True,
                )
                return result
            except Exception as exc:
                last_error = exc
                self._telemetry.record_call(
                    model=kwargs.get("model", "unknown"),
                    provider=provider.name,
                    latency_ms=0,
                    tokens=0,
                    success=False,
                    error=str(exc),
                )
                logger.warning("Provider %s failed: %s", provider.name, exc)
        raise ProviderError(f"All providers failed. Last error: {last_error}")
