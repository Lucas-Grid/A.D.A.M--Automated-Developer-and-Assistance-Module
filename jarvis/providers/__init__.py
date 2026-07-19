"""Provider adapters and registry."""
from __future__ import annotations

from jarvis.providers.base import LLMProvider
from jarvis.providers.local import LocalProvider
from jarvis.providers.ollama import OllamaProvider
from jarvis.providers.openai_compat import OpenAICompatibleProvider
from jarvis.providers.registry import (
    build_providers,
    get_provider,
    provider_from_spec,
)

__all__ = [
    "LLMProvider",
    "LocalProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "build_providers",
    "get_provider",
    "provider_from_spec",
]
