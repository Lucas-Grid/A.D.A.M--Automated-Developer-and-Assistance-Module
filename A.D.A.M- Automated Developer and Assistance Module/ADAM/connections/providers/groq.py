"""Groq provider."""
from __future__ import annotations

from ADAM.core.config import get_settings
from ADAM.connections.providers.openai_compat import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        s = get_settings()
        super().__init__(
            name="groq",
            base_url=s.groq_base_url,
            api_key=s.groq_api_key,
        )
