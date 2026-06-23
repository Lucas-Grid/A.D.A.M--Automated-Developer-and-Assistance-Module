"""LLM streaming support."""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterator

from ADAM.llm.telemetry import LLMTelemetry

logger = logging.getLogger(__name__)


class StreamHandler:
    """Handle streaming LLM responses."""

    def __init__(self, telemetry: LLMTelemetry | None = None) -> None:
        self._telemetry = telemetry or LLMTelemetry()

    def stream_chunks(self, iterator: Iterator[str], model: str, provider: str) -> Iterator[dict[str, Any]]:
        for chunk in iterator:
            yield {
                "content": chunk,
                "done": False,
                "model": model,
                "provider": provider,
            }
        yield {"content": "", "done": True, "model": model, "provider": provider}


def stream_with_callback(
    provider: Any,
    callback: Callable[[str], None],
    model: str,
    messages: list[dict[str, Any]],
    **kwargs: Any,
) -> str:
    """Stream completion and invoke callback for each token."""
    telemetry = LLMTelemetry()
    buffer: list[str] = []
    with telemetry.timer() as t:
        for chunk in provider.stream(model=model, messages=messages, **kwargs):
            token = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)
            callback(token)
            buffer.append(token)
    telemetry.record_call(
        model=model,
        provider=provider.name,
        latency_ms=getattr(t, "elapsed_ms", 0),
        tokens=len(buffer),
        success=True,
    )
    return "".join(buffer)
