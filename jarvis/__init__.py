"""Jarvis - a desktop-centric autonomous AI assistant.

A small, modular, dependency-light reference implementation of the
"Desktop-Jarvis" architecture: a multi-provider LLM router, a tool-calling
agent/orchestrator (MRKL-style plan-then-act loop), a sandboxed code
executor, and a short/long-term memory layer.

The built-in *local* provider is fully deterministic and needs no API keys or
network, so the whole loop can be exercised and proven on any machine. Real
providers (Ollama, OpenAI-compatible endpoints such as Nous/OpenRouter/OpenAI,
and Anthropic) are wired as pluggable adapters.
"""
from __future__ import annotations

from jarvis.config import Config, load_config
from jarvis.orchestrator import Orchestrator
from jarvis.providers.registry import build_providers
from jarvis.tools.registry import ToolRegistry

__version__ = "0.1.0"

__all__ = [
    "Config",
    "load_config",
    "Orchestrator",
    "build_providers",
    "ToolRegistry",
    "__version__",
]
