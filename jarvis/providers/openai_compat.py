"""OpenAI-compatible provider (OpenAI, OpenRouter, Nous, Nvidia NIM, etc.).

These services expose an OpenAI-style /v1/chat/completions endpoint. We call
it directly with ``requests`` so there are no extra SDK dependencies.
"""
from __future__ import annotations

import json
from typing import Any, Sequence

import requests

from jarvis.providers.base import LLMProvider
from jarvis.types import GenerationResult, Message


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compat"
    model = ""

    # vendor -> default base_url (overridable via spec.base_url)
    DEFAULT_BASE = {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "nous": "https://api.nousresearch.com/v1",
        "anthropic_compat": "https://api.anthropic.com/v1",
        "openai_compat": "https://api.openai.com/v1",
    }

    def __init__(self, model: str, base_url: str = "", api_key: str = "", vendor: str = "openai", timeout: int = 120, **kwargs: Any) -> None:
        super().__init__(model=model, **kwargs)
        self.vendor = vendor
        self.base_url = (base_url or self.DEFAULT_BASE.get(vendor, "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout

    def generate(
        self,
        messages: Sequence[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Sequence[str] | None = None,
    ) -> GenerationResult:
        if not self.model:
            raise ValueError(f"Provider '{self.vendor}' requires a model name in config.")
        system, chat = self.split_roles(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": chat,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if system:
            payload["messages"].insert(0, {"role": "system", "content": system})
        if stop:
            payload["stop"] = list(stop)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        last_err: Exception | None = None
        # Transient failures (429 rate-limit, 5xx, timeouts) are retried with
        # exponential backoff + jitter so a single run survives NIM's throttling
        # windows instead of burning the agent's step budget. Auth errors
        # (401/403) are NOT transient -- retrying them just loops on a dead key,
        # so we surface them immediately with the offending URL.
        for attempt in range(4):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return GenerationResult(
                    text=text,
                    provider=self.vendor,
                    model=self.model,
                    usage=usage,
                )
            except requests.exceptions.Timeout:
                last_err = RuntimeError(f"{self.vendor} request timed out (attempt {attempt + 1}/4)")
            except requests.exceptions.HTTPError as e:
                code = getattr(e.response, "status_code", 0)
                url = getattr(e.response, "url", f"{self.base_url}/chat/completions")
                if code == 401:
                    raise PermissionError(
                        f"401 Unauthorized calling {url}. The API key is missing, "
                        f"invalid, or not authorized for model '{self.model}'. "
                        f"Check NVIDIA_NIM_API_KEY (or your provider key) is exported "
                        f"in the shell that launched Jarvis."
                    ) from e
                if code == 403:
                    raise PermissionError(
                        f"403 Forbidden calling {url}. Your key is not authorized for "
                        f"model '{self.model}' (or this endpoint)."
                    ) from e
                # Retry on 5xx and 429 (transient rate-limiting); surface other 4xx.
                if code >= 500 or code == 429:
                    last_err = e
                else:
                    raise
            # Back off before the next attempt (skip sleep on the last try).
            if attempt < 3:
                import time as _time
                import random as _random
                import sys as _sys

                status = ""
                if isinstance(last_err, requests.exceptions.HTTPError):
                    status = f"{getattr(last_err.response, 'status_code', 0)} "
                if isinstance(last_err, requests.exceptions.HTTPError) and getattr(last_err.response, "status_code", 0) == 429:
                    wait = min(30.0, (2 ** attempt) * 4 + _random.uniform(0, 3))
                else:
                    wait = min(20.0, (2 ** attempt) * 2 + _random.uniform(0, 2))
                _sys.stderr.write(f"  [provider backoff] {self.vendor} {status}retrying in {wait:.1f}s...\n")
                _sys.stderr.flush()
                _time.sleep(wait)
        raise last_err or RuntimeError(f"{self.vendor} request failed")

    def stream_generate(
        self,
        messages: Sequence[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Sequence[str] | None = None,
    ):
        """Yield text deltas (str) as the model generates them (SSE streaming).

        Falls back to yielding the whole text once if the endpoint rejects the
        streaming request. This is what lets the HUD + voice reply start the
        instant the first tokens exist instead of after the full answer.
        """
        if not self.model:
            raise ValueError(f"Provider '{self.vendor}' requires a model name in config.")
        system, chat = self.split_roles(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": chat,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            payload["messages"].insert(0, {"role": "system", "content": system})
        if stop:
            payload["stop"] = list(stop)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            with requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=True,
            ) as resp:
                resp.raise_for_status()
                for raw in resp.iter_lines():
                    if not raw:
                        continue
                    line = raw.decode("utf-8", "replace")
                    if line.startswith("data:"):
                        chunk = line[len("data:"):].strip()
                        if chunk == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk)
                            delta = data["choices"][0]["delta"].get("content") or ""
                            if delta:
                                yield delta
                        except Exception:
                            continue
        except Exception as e:
            # Endpoint/streaming hiccup: emit nothing here; the caller's
            # fallback (non-streaming generate) handles recovery.
            raise e

    def list_models(self) -> list[str]:
        """Enumerate models available under this provider's credentials."""
        if not self.api_key and self.vendor not in ("local", "ollama"):
            return []
        try:
            import requests

            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            resp = requests.get(f"{self.base_url}/models", headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", []) if isinstance(data, dict) else data
            return [m.get("id") for m in items if m.get("id")]
        except Exception:
            return []
