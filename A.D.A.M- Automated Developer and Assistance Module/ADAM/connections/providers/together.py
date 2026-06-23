"""Together.ai provider."""
from __future__ import annotations

from ADAM.core.config import get_settings
from ADAM.connections.providers.openai_compat import OpenAICompatProvider


class TogetherProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        s = get_settings()
        super().__init__(
            name="together",
            base_url=s.together_base_url,
            api_key=s.together_api_key,
        )
