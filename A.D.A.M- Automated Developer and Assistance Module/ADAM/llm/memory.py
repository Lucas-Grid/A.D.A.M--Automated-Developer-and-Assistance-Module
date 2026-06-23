"""LLM memory integration: persist and load conversation context."""
from __future__ import annotations

import json
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.memory.store import get_memory


class LLMMemory:
    """Store and retrieve LLM-related memory entries."""

    def __init__(self) -> None:
        self._memory = get_memory()

    def save_context(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        key = f"llm.context.{session_id}"
        self._memory.set(key, json.dumps(messages))

    def load_context(self, session_id: str) -> list[dict[str, Any]]:
        key = f"llm.context.{session_id}"
        row = self._memory.get(key)
        return json.loads(row["value"]) if row else []
