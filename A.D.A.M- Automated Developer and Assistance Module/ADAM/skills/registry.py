"""Skill registry: metadata catalog of available skills."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ADAM.core.exceptions import SkillError


@dataclass
class SkillManifest:
    name: str
    description: str
    version: str = "0.1.0"
    entrypoint: str = ""
    enabled: bool = True
    tags: List[str] = field(default_factory=list)


class SkillRegistry:
    """In-memory registry of skill manifests."""

    def __init__(self) -> None:
        self._items: dict[str, SkillManifest] = {}

    def register(self, manifest: SkillManifest) -> None:
        if manifest.name in self._items:
            raise SkillError(f"Skill '{manifest.name}' is already registered")
        self._items[manifest.name] = manifest

    def unregister(self, name: str) -> None:
        self._items.pop(name, None)

    def get(self, name: str) -> SkillManifest:
        try:
            return self._items[name]
        except KeyError:
            raise SkillError(f"Skill '{name}' is not registered")

    def list(self) -> List[SkillManifest]:
        return list(self._items.values())

    def clear(self) -> None:
        self._items.clear()
