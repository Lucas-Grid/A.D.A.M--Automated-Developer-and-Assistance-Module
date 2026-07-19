"""Base class for LLM providers."""
from __future__ import annotations

from typing import Any, Optional, Sequence

from jarvis.providers.cache import ResponseCache
from jarvis.types import GenerationResult, Message


class LLMProvider:
    """Common interface every provider implements.

    ``generate`` turns a list of :class:`Message` objects into a
    :class:`GenerationResult`. Providers that call a real API may ignore the
    ``system`` role and instead rely on a dedicated system parameter.

    An optional ``cache`` (§4.3) transparently memoises identical
    (model, prompt) generations; set ``cache`` to a ``ResponseCache`` with a
    positive ttl to enable it.
    """

    name = "base"
    model = ""

    def __init__(self, model: str = "", **kwargs: Any) -> None:
        self.model = model or self.model
        self.kwargs = kwargs
        # optional TTL cache (§4.3); None disables caching
        self.cache: Optional[ResponseCache] = kwargs.pop("cache", None)

    def _prompt_key(self, messages: Sequence[Message]) -> str:
        return "\n".join(f"{m.role}:{m.content}" for m in messages)

    def generate(
        self,
        messages: Sequence[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Sequence[str] | None = None,
    ) -> GenerationResult:
        raise NotImplementedError

    def generate_cached(
        self,
        messages: Sequence[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Sequence[str] | None = None,
    ) -> GenerationResult:
        """Like :meth:`generate` but honours ``self.cache`` when set."""
        if self.cache is None:
            return self.generate(messages, max_tokens, temperature, stop)
        key = self._prompt_key(messages)
        cached = self.cache.get(self.name, self.model, key)
        if cached is not None:
            cached.cached = True  # type: ignore[attr-defined]
            return cached
        result = self.generate(messages, max_tokens, temperature, stop)
        self.cache.put(self.name, self.model, key, result)
        return result

    def list_models(self) -> list[str]:
        """Return models available under this provider's credentials (override in subclasses)."""
        return []

    # --- helpers shared by providers ------------------------------------
    @staticmethod
    def split_roles(messages: Sequence[Message]) -> tuple[str, list[dict[str, str]]]:
        """Return (system_text, chat_pairs) for OpenAI-style APIs."""
        system_parts: list[str] = []
        chat: list[dict[str, str]] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            else:
                chat.append({"role": m.role, "content": m.content})
        return "\n\n".join(system_parts), chat
