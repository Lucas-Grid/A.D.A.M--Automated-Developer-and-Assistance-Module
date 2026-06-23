"""LLM router: select best model/provider for a task."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.connections.model_registry import get_model_registry
from ADAM.core.exceptions import ModelRegistryError
from ADAM.llm.telemetry import LLMTelemetry

logger = logging.getLogger(__name__)


class LLMRouter:
    """Route LLM requests to the best available model/provider."""

    def __init__(self, telemetry: LLMTelemetry | None = None) -> None:
        self._registry = get_model_registry()
        self._telemetry = telemetry or LLMTelemetry()

    def select(self, task_type: str = "chat", preferred_model: str | None = None) -> dict[str, Any]:
        if preferred_model:
            model = self._registry.get(preferred_model)
            if model:
                return model
            logger.warning("Preferred model '%s' not found, falling back to selection", preferred_model)

        candidates = [
            m for m in self._registry.list_models(status="available")
            if task_type == "chat" and m.get("supports_chat")
        ]
        if not candidates:
            raise ModelRegistryError(f"No available models for task type '{task_type}'")
        return candidates[0]
