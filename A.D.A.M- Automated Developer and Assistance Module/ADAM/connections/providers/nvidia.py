"""NVIDIA NIM provider."""
from __future__ import annotations

from ADAM.core.config import get_settings
from ADAM.connections.providers.openai_compat import OpenAICompatProvider


class NvidiaProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        s = get_settings()
        super().__init__(
            name="nvidia",
            base_url=s.nvidia_base_url,
            api_key=s.nvidia_api_key,
        )
