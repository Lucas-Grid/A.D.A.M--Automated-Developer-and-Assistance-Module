"""Configuration for Jarvis, loaded from a YAML file with sensible defaults.

No external YAML library is required: we use Python's stdlib ``tomllib``
(Py3.11+) when available, otherwise a tiny built-in parser for the small
subset of YAML we use. A ``.jarvis.yaml`` in the working directory (or a path
given via JARVIS_CONFIG) overrides defaults.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProviderSpec:
    """Definition of one LLM provider.

    ``type`` selects the adapter: local | ollama | openai | anthropic.
    Only the fields relevant to the type are used.
    """

    name: str
    type: str
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    enabled: bool = True
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    providers: list[ProviderSpec] = field(default_factory=list)
    default_provider: str = "local"
    sandbox: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    max_steps: int = 12
    require_confirmation: bool = True  # human-in-the-loop gate for risky tools
    workspace: str = "."
    cache: dict[str, Any] = field(default_factory=dict)  # §4.3 response cache: {ttl_seconds}
    model_selector: dict[str, Any] = field(default_factory=dict)  # §4.2 weights

    def provider(self, name: Optional[str] = None) -> ProviderSpec:
        name = name or self.default_provider
        for p in self.providers:
            if p.name == name and p.enabled:
                return p
        # fall back to the local provider which is always available
        for p in self.providers:
            if p.type == "local":
                return p
        raise RuntimeError("No provider available (not even local).")


# --- minimal YAML reader (subset: nested maps, lists, scalars) ----------------
def _coerce(scalar: str) -> Any:
    s = scalar.strip()
    if s == "" or s.lower() in ("null", "~", "none"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_yaml(text: str) -> dict[str, Any]:
    """Parse a tiny YAML subset: 2-space indented maps, '- ' lists, scalars."""
    root: dict[str, Any] = {}
    # stack of (indent, container)
    stack: list[tuple[int, Any]] = [(-1, root)]
    list_ctx: dict[int, list[Any]] = {}  # indent -> pending list container
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        # strip inline comments (naive: not inside quotes)
        line = raw
        if "#" in line:
            in_q = False
            q = ""
            out = []
            for ch in line:
                if ch in ("'", '"') and not in_q:
                    in_q = True
                    q = ch
                elif ch == q and in_q:
                    in_q = False
                elif ch == "#" and not in_q:
                    break
                out.append(ch)
            line = "".join(out)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith("- "):
            item = content[2:].strip()
            lst = list_ctx.get(stack[-1][0])
            if lst is None:
                lst = []
                list_ctx[stack[-1][0]] = lst
                # figure type: if parent is dict, key already set? handled below
            if ":" in item and not (item.startswith('"') or item.startswith("'")):
                key, _, val = item.partition(":")
                d: dict[str, Any] = {}
                d[key.strip()] = _coerce(val) if val.strip() else None
                lst.append(d)
                stack.append((indent + 2, d))
            else:
                lst.append(_coerce(item))
            # ensure list is attached to parent
            if isinstance(parent, dict) and not getattr(parent, "_list_attached", False):
                # find the key whose value should be this list; attach lazily
                pass
            continue
        key, _, val = content.partition(":")
        key = key.strip()
        if val.strip() == "":
            new: dict[str, Any] = {}
            if isinstance(parent, dict):
                parent[key] = new
                stack.append((indent, new))
                list_ctx[indent] = []
            elif isinstance(parent, list):
                parent.append(new)
                stack.append((indent, new))
        else:
            if isinstance(parent, dict):
                parent[key] = _coerce(val)
    return root


def _load_dict(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return {}
    # Prefer PyYAML if present, else fallback parser.
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except Exception:
        return _parse_yaml(text)


def load_config(path: Optional[str] = None) -> Config:
    path = path or os.environ.get("JARVIS_CONFIG") or os.path.join(os.getcwd(), ".jarvis.yaml")
    raw = _load_dict(path)
    providers: list[ProviderSpec] = []
    for p in raw.get("providers", []) or []:
        if isinstance(p, dict):
            providers.append(
                ProviderSpec(
                    name=p.get("name", "unnamed"),
                    type=p.get("type", "local"),
                    model=p.get("model", ""),
                    base_url=p.get("base_url", ""),
                    api_key=p.get("api_key", ""),
                    enabled=bool(p.get("enabled", True)),
                    kwargs=p.get("kwargs", {}) or {},
                )
            )
    if not providers:
        providers.append(ProviderSpec(name="local", type="local", model="deterministic"))
    cfg = Config(
        providers=providers,
        default_provider=raw.get("default_provider", "local"),
        sandbox=raw.get("sandbox", {}) or {},
        memory=raw.get("memory", {}) or {},
        max_steps=int(raw.get("max_steps", 12)),
        require_confirmation=bool(raw.get("require_confirmation", True)),
        workspace=raw.get("workspace", "."),
        cache=raw.get("cache", {}) or {},
        model_selector=raw.get("model_selector", {}) or {},
    )
    # Expand `env:VAR` references so secrets stay out of config files.
    for _p in cfg.providers:
        if isinstance(_p.api_key, str) and _p.api_key.startswith("env:"):
            _p.api_key = os.environ.get(_p.api_key[4:], "")
    return cfg
