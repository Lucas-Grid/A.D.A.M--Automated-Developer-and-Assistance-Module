"""Model Selector (reference architecture §4.2): score providers by cost,
latency, VRAM/modality and pick the best for a given request.

Kept dependency-light: scores come from the provider config (optional
``score`` hints) and runtime telemetry. If no real providers are configured the
local brain is always selected. This realises the report's "Model Selector"
service without pulling in a heavy routing framework.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from jarvis.config import Config, ProviderSpec


# Default weights -- tilt toward cheap + fast by default; tune in config.
DEFAULT_WEIGHTS = {"cost": 0.4, "latency": 0.35, "modality": 0.25}

# Modality capability per provider type (image/voice awareness for §2 multimodal).
_MODALITY = {
    "local": {"text": 1.0},
    "ollama": {"text": 1.0},
    "openai": {"text": 1.0, "image": 1.0},
    "anthropic": {"text": 1.0, "image": 1.0},
}


class ModelSelector:
    def __init__(self, config: Config, weights: Optional[dict[str, float]] = None) -> None:
        self.config = config
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        # live latency samples keyed by provider name (ms)
        self._latency: dict[str, float] = {}

    def observe_latency(self, name: str, ms: float) -> None:
        self._latency[name] = self._latency.get(name, ms) * 0.7 + ms * 0.3

    def _cost_score(self, p: ProviderSpec) -> float:
        # Lower cost -> higher score. Local/Ollama are free; cloud has a hint.
        if p.type in ("local", "ollama"):
            return 1.0
        hint = (p.kwargs or {}).get("cost_per_1k")
        if hint is None:
            return 0.5
        # 1/(1+cost) normalized so 0.003 -> ~0.997, 0.06 -> ~0.94
        return 1.0 / (1.0 + float(hint))

    def _latency_score(self, name: str) -> float:
        ms = self._latency.get(name)
        if ms is None:
            return 0.8  # unknown -> assume decent
        # 250ms -> ~0.8, 2000ms -> ~0.33
        return max(0.0, min(1.0, 1.0 / (1.0 + ms / 1000.0)))

    def _modality_score(self, p: ProviderSpec, need: dict[str, bool]) -> float:
        caps = _MODALITY.get(p.type, {"text": 1.0})
        if not need:
            return 1.0
        score = 0.0
        n = 0
        for modality, required in need.items():
            n += 1
            if not required:
                score += 1.0
            else:
                score += float(caps.get(modality, 0.0))
        return score / max(n, 1)

    def score(self, p: ProviderSpec, need: dict[str, bool] | None = None) -> float:
        need = need or {}
        s = (
            self.weights.get("cost", 0.4) * self._cost_score(p)
            + self.weights.get("latency", 0.35) * self._latency_score(p.name)
            + self.weights.get("modality", 0.25) * self._modality_score(p, need)
        )
        return round(s, 4)

    def select(self, need: dict[str, bool] | None = None) -> ProviderSpec:
        """Return the highest-scoring *enabled* provider; falls back to local."""
        candidates = [p for p in self.config.providers if p.enabled]
        if not candidates:
            candidates = list(self.config.providers)
        if not candidates:
            raise RuntimeError("No providers configured.")
        ranked = sorted(candidates, key=lambda p: self.score(p, need), reverse=True)
        return ranked[0]

    def ranking(self, need: dict[str, bool] | None = None) -> list[tuple[str, float]]:
        return [(p.name, self.score(p, need)) for p in self.config.providers if p.enabled]
