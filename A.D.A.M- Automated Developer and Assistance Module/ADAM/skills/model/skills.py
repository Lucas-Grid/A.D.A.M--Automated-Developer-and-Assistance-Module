"""Model skills for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.core.exceptions import ProviderError
from ADAM.connections.model_registry import get_model_registry
from ADAM.connections.providers.anthropic import AnthropicProvider
from ADAM.connections.providers.base import BaseProvider
from ADAM.connections.providers.gemini import GeminiProvider
from ADAM.connections.providers.groq import GroqProvider
from ADAM.connections.providers.mistral import MistralProvider
from ADAM.connections.providers.nvidia import NvidiaProvider
from ADAM.connections.providers.ollama import OllamaProvider
from ADAM.connections.providers.openai import OpenAIProvider
from ADAM.connections.providers.openrouter import OpenRouterProvider
from ADAM.connections.providers.together import TogetherProvider
from ADAM.memory.store import get_memory
from ADAM.skills.base import BaseSkill

PROVIDERS: dict[str, type[BaseProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "together": TogetherProvider,
    "mistral": MistralProvider,
    "nvidia": NvidiaProvider,
}


class ModelDiscoverSkill(BaseSkill):
    name = "model.discover"
    description = "Discover and register models from all configured providers"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        providers = params.get("providers")
        if providers is None:
            providers = list(PROVIDERS.keys())
        registry = get_model_registry()
        discovered: list[dict[str, Any]] = []
        for pname in providers:
            cls = PROVIDERS.get(pname)
            if not cls:
                continue
            provider = cls()
            try:
                models = provider.list_models()
                for m in models:
                    registry.register(m)
                    discovered.append(m)
            except Exception as exc:
                discovered.append({"provider": pname, "error": str(exc)})
        return {"discovered": discovered}


class ModelListSkill(BaseSkill):
    name = "model.list"
    description = "List registered models, optionally filtered by provider or status"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        registry = get_model_registry()
        models = registry.list_models(
            provider=params.get("provider"),
            status=params.get("status"),
        )
        return {"models": models}


class ModelHealthSkill(BaseSkill):
    name = "model.health"
    description = "Check health across one or more providers"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        providers = params.get("providers")
        if providers is None:
            providers = list(PROVIDERS.keys())
        results = {}
        for pname in providers:
            cls = PROVIDERS.get(pname)
            if not cls:
                continue
            provider = cls()
            try:
                results[pname] = provider.health()
            except Exception as exc:
                results[pname] = {"status": "error", "error": str(exc)}
        return {"health": results}


class ModelSelectSkill(BaseSkill):
    name = "model.select"
    description = "Select a model and persist selection into Memory Store"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        model_id = params.get("model_id")
        if not model_id:
            raise ValueError("Missing 'model_id'")
        registry = get_model_registry()
        model = registry.get(model_id)
        if not model:
            raise ValueError(f"Model '{model_id}' not found")
        memory = get_memory()
        memory.set("models.selected", model_id, tags=["models", "selected"])
        memory.set("models.available", model_id, tags=["models", "available"])
        return {"selected": model}
