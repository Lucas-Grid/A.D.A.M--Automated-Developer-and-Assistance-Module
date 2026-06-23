"""OpenAI provider."""
from __future__ import annotations

from ADAM.core.config import get_settings
from ADAM.connections.providers.openai_compat import OpenAICompatProvider


class OpenAIProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        s = get_settings()
        super().__init__(
            name="openai",
            base_url=s.openai_base_url,
            api_key=s.openai_api_key,
        )
