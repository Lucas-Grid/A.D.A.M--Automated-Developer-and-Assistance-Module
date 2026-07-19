"""Provider registry: build and look up providers from config."""
from __future__ import annotations

from typing import Optional

from jarvis.config import Config, ProviderSpec
from jarvis.providers.base import LLMProvider
from jarvis.providers.cache import ResponseCache
from jarvis.providers.local import LocalProvider
from jarvis.providers.ollama import OllamaProvider
from jarvis.providers.openai_compat import OpenAICompatibleProvider

_REGISTRY: dict[str, LLMProvider] = {}


def provider_from_spec(spec: ProviderSpec, cache: Optional[ResponseCache] = None) -> LLMProvider:
    if spec.type == "local":
        return LocalProvider(model=spec.model or "deterministic", cache=cache)
    if spec.type == "ollama":
        return OllamaProvider(
            model=spec.model or "llama3.1",
            base_url=spec.base_url or "http://localhost:11434",
            cache=cache,
            **spec.kwargs,
        )
    if spec.type in ("openai", "openai_compat", "openrouter", "nous", "anthropic_compat"):
        return OpenAICompatibleProvider(
            model=spec.model,
            base_url=spec.base_url or "https://api.openai.com/v1",
            api_key=spec.api_key,
            vendor=spec.type,
            cache=cache,
            **spec.kwargs,
        )
    raise ValueError(f"Unknown provider type: {spec.type!r}")


def build_providers(cfg: Config) -> dict[str, LLMProvider]:
    """Instantiate all enabled providers and register them by name.

    A response cache (§4.3) is attached to every provider when config
    ``cache.ttl_seconds`` > 0, so repeat prompts hit the cache instead of a
    paid endpoint.
    """
    _REGISTRY.clear()
    cache_cfg = cfg.cache or {}
    ttl = float(cache_cfg.get("ttl_seconds") or 0)
    cache = ResponseCache(ttl) if ttl > 0 else None
    for spec in cfg.providers:
        if not spec.enabled:
            continue
        _REGISTRY[spec.name] = provider_from_spec(spec, cache)
    # Always ensure a local provider exists as a fallback.
    if "local" not in _REGISTRY:
        _REGISTRY["local"] = LocalProvider(cache=cache)
    return dict(_REGISTRY)


def get_provider(name: Optional[str] = None, default: str = "local") -> LLMProvider:
    if not _REGISTRY:
        _REGISTRY["local"] = LocalProvider()
    return _REGISTRY.get(name or default) or _REGISTRY["local"]


def build_selector(cfg: Config):
    """Construct a ModelSelector (§4.2) from config weights."""
    from jarvis.providers.selector import ModelSelector

    weights = (cfg.model_selector or {}).get("weights")
    return ModelSelector(cfg, weights)


def discover_models(cfg: Optional[Config] = None) -> dict[str, list[str]]:
    """Enumerate models available under each configured provider's credentials.

    Returns {provider_name: [model_ids, ...]} so the user can pick any model
    from any provider they have access to.
    """
    cfg = cfg or load_config_if_present()
    if cfg is None:
        return {}
    out: dict[str, list[str]] = {}
    for spec in cfg.providers:
        if not spec.enabled:
            continue
        try:
            prov = provider_from_spec(spec)
            out[spec.name] = prov.list_models() or [spec.model]
        except Exception:
            out[spec.name] = [spec.model]
    return out


def load_config_if_present() -> Optional[Config]:
    from jarvis.config import load_config

    try:
        return load_config()
    except Exception:
        return None
