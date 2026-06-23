"""ECC telemetry tracking."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ECCTelemetry:
    """Track ECC reasoning metrics."""

    def __init__(self) -> None:
        self._enabled = True

    def record(self, event: str, data: dict[str, Any]) -> None:
        if not self._enabled:
            return
        data["event"] = event
        logger.debug("ECC telemetry: %s", json.dumps(data))

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
