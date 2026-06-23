"""OpenRouter provider."""
from __future__ import annotations

from ADAM.core.config import get_settings
from ADAM.connections.providers.openai_compat import OpenAICompatProvider


class OpenRouterProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        s = get_settings()
        super().__init__(
            name="openrouter",
            base_url=s.openrouter_base_url,
            api_key=s.openrouter_api_key,
        )
