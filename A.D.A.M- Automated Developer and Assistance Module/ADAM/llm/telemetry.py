"""LLM telemetry tracking."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from ADAM.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMTelemetry:
    """Track LLM execution metrics."""

    def __init__(self) -> None:
        self._enabled = True

    def record(self, metrics: dict[str, Any]) -> None:
        if not self._enabled:
            return
        logger.debug("LLM telemetry: %s", json.dumps(metrics))

    def record_call(self, model: str, provider: str, latency_ms: int, tokens: int, success: bool, error: str | None = None) -> None:
        self.record({
            "event": "llm.call",
            "model": model,
            "provider": provider,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "success": success,
            "error": error,
        })

    def timer(self) -> "_Timer":
        return _Timer()


class _Timer:
    def __init__(self) -> None:
        self._start: float = 0.0

    def __enter__(self) -> "_Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)
