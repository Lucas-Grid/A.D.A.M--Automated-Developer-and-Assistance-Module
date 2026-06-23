"""ECC memory: persist observations, reflections, lessons, decisions."""
from __future__ import annotations

import json
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.memory.store import get_memory


class ECCMemory:
    """Store ECC-related memory entries."""

    def __init__(self) -> None:
        self._memory = get_memory()

    def _load_list(self, key: str) -> list[dict[str, Any]]:
        row = self._memory.get(key)
        if not row:
            return []
        try:
            value = json.loads(row["value"])
            return value if isinstance(value, list) else []
        except json.JSONDecodeError:
            return []

    def _save_list(self, key: str, items: list[dict[str, Any]]) -> None:
        self._memory.set(key, json.dumps(items))

    def add_observation(self, observation: dict[str, Any]) -> None:
        items = self._load_list("ecc.observations")
        items.append(observation)
        self._save_list("ecc.observations", items)

    def add_reflection(self, reflection: dict[str, Any]) -> None:
        items = self._load_list("ecc.reflections")
        items.append(reflection)
        self._save_list("ecc.reflections", items)

    def add_lesson(self, lesson: str) -> None:
        items = self._load_list("ecc.lessons")
        items.append({"lesson": lesson})
        self._save_list("ecc.lessons", items)

    def add_decision(self, decision: dict[str, Any]) -> None:
        items = self._load_list("ecc.decisions")
        items.append(decision)
        self._save_list("ecc.decisions", items)

    def get_observations(self) -> list[dict[str, Any]]:
        return self._load_list("ecc.observations")

    def get_reflections(self) -> list[dict[str, Any]]:
        return self._load_list("ecc.reflections")

    def get_lessons(self) -> list[dict[str, Any]]:
        return self._load_list("ecc.lessons")

    def get_decisions(self) -> list[dict[str, Any]]:
        return self._load_list("ecc.decisions")
