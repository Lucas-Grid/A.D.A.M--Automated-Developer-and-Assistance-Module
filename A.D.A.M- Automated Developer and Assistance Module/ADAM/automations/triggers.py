"""Trigger system: registration and matching for automation triggers."""
from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseTrigger(ABC):
    """Base trigger contract."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def should_fire(self, context: dict[str, Any]) -> bool:
        """Return True if trigger conditions are met."""

    @abstractmethod
    def start(self, callback) -> None:
        """Begin watching for trigger conditions."""

    @abstractmethod
    def stop(self) -> None:
        """Stop watching."""


class ScheduleTrigger(BaseTrigger):
    def should_fire(self, context: dict[str, Any]) -> bool:
        return False

    def start(self, callback) -> None:
        pass

    def stop(self) -> None:
        pass


class StartupTrigger(BaseTrigger):
    def should_fire(self, context: dict[str, Any]) -> bool:
        return context.get("event") == "startup"

    def start(self, callback) -> None:
        pass

    def stop(self) -> None:
        pass


class ManualTrigger(BaseTrigger):
    def should_fire(self, context: dict[str, Any]) -> bool:
        return context.get("event") == "manual"

    def start(self, callback) -> None:
        pass

    def stop(self) -> None:
        pass


class FileSystemTrigger(BaseTrigger):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.watch_path = Path(config.get("path", "."))
        self.patterns = config.get("patterns", ["*"])
        self._running = False

    def should_fire(self, context: dict[str, Any]) -> bool:
        return context.get("event") == "filesystem"

    def start(self, callback) -> None:
        self._running = True

        def _watch():
            while self._running:
                time.sleep(1)

        threading.Thread(target=_watch, daemon=True).start()

    def stop(self) -> None:
        self._running = False


class TriggerManager:
    """Manage trigger instances."""

    def __init__(self) -> None:
        self._triggers: dict[str, BaseTrigger] = {}

    def register(self, trigger_type: str, config: dict[str, Any]) -> BaseTrigger:
        mapping = {
            "schedule": ScheduleTrigger,
            "startup": StartupTrigger,
            "manual": ManualTrigger,
            "filesystem": FileSystemTrigger,
        }
        cls = mapping.get(trigger_type)
        if not cls:
            raise ValueError(f"Unsupported trigger type: {trigger_type}")
        trigger = cls(config)
        self._triggers[trigger_type] = trigger
        return trigger

    def get(self, trigger_type: str) -> Optional[BaseTrigger]:
        return self._triggers.get(trigger_type)

    def evaluate(self, trigger_type: str, context: dict[str, Any]) -> bool:
        trigger = self._triggers.get(trigger_type)
        if not trigger:
            return False
        return trigger.should_fire(context)


# Singleton
_manager: Optional[TriggerManager] = None


def get_trigger_manager() -> TriggerManager:
    global _manager
    if _manager is None:
        _manager = TriggerManager()
    return _manager


def reset_trigger_manager() -> None:
    global _manager
    _manager = None
