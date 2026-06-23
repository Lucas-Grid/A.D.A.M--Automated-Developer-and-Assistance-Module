"""Mistral AI provider."""
from __future__ import annotations

from ADAM.core.config import get_settings
from ADAM.connections.providers.openai_compat import OpenAICompatProvider


class MistralProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        s = get_settings()
        super().__init__(
            name="mistral",
            base_url=s.mistral_base_url,
            api_key=s.mistral_api_key,
        )
