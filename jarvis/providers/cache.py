"""Provider response cache (reference architecture §4.3).

A tiny in-memory TTL cache keyed by (provider, model, prompt-hash). Reduces
repeat calls to paid endpoints and latency. Opt-in: the orchestrator/CLI enable
it via config ``cache.ttl_seconds``. No external deps.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Optional


class ResponseCache:
    def __init__(self, ttl_seconds: float = 0.0) -> None:
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    @staticmethod
    def _key(provider: str, model: str, prompt: str) -> str:
        h = hashlib.sha1(f"{provider}|{model}|{prompt}".encode("utf-8")).hexdigest()[:16]
        return h

    def get(self, provider: str, model: str, prompt: str) -> Optional[Any]:
        if self.ttl <= 0:
            return None
        k = self._key(provider, model, prompt)
        item = self._store.get(k)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > self.ttl:
            self._store.pop(k, None)
            return None
        return value

    def put(self, provider: str, model: str, prompt: str, value: Any) -> None:
        if self.ttl <= 0:
            return
        self._store[self._key(provider, model, prompt)] = (time.time(), value)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)
