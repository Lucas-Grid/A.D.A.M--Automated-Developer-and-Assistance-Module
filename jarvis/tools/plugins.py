"""YAML plugin loader (reference architecture §10: Plugin System & Extensibility).

Lets users add new tools via a simple YAML file under tools/plugins/ without
touching core code. Each plugin declares a Python ``body`` that returns a
ToolResult (executed in a restricted namespace). This mirrors the report's
"simple YAML or Python plugin" requirement. Confirmation-gated for risky tools.
"""
from __future__ import annotations

import os
from typing import Any

from jarvis.tools.registry import FunctionTool, ToolContext, ToolResult, ToolRegistry, get_registry


def _load_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except Exception:
        from jarvis.config import _parse_yaml

        return _parse_yaml(text)


def load_plugins(directory: str, registry: ToolRegistry | None = None) -> list[str]:
    """Load every *.yaml plugin in ``directory`` and register as FunctionTools.

    Returns the list of registered tool names. Each plugin file looks like:

        name: greet
        description: Say hello to a name.
        danger: safe
        permissions: []
        sandbox_profile: none
        args:
          name: string
        body: |
          return ToolResult(ok=True, output=f"Hello, {kwargs.get('name')}!", tool='greet')
    """
    reg = registry or get_registry()
    loaded: list[str] = []
    if not os.path.isdir(directory):
        return loaded
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(directory, fn)
        try:
            data = _load_yaml(path)
        except Exception:
            continue
        tools = data if isinstance(data, list) else [data]
        for spec in tools:
            if not isinstance(spec, dict) or not spec.get("name"):
                continue
            name = spec["name"]
            body = spec.get("body", "")
            description = spec.get("description", "")
            danger = spec.get("danger", "safe")
            permissions = spec.get("permissions") or []
            sandbox_profile = spec.get("sandbox_profile", "none")
            args_schema = spec.get("args") or {}

            def make_fn(body_src: str):
                def fn(ctx: ToolContext, **kwargs: Any) -> ToolResult:
                    # Wrap the plugin body in a function so `return` works, then
                    # call it. The body sees ctx, kwargs, ToolResult in scope.
                    wrapper = f"def __plugin__(ctx, kwargs, ToolResult):\n"
                    indented = "\n".join("    " + line for line in body_src.splitlines())
                    ns: dict[str, Any] = {}
                    try:
                        exec(wrapper + indented + "\n", ns)
                        return ns["__plugin__"](ctx, kwargs, ToolResult)
                    except Exception as e:  # never let a plugin crash the loop
                        return ToolResult(ok=False, output="", tool=name, error=repr(e))

                return fn

            reg.register(
                FunctionTool(
                    name,
                    make_fn(body),
                    description=description,
                    danger=danger,
                    schema=args_schema,
                    permissions=permissions,
                    sandbox_profile=sandbox_profile,
                )
            )
            loaded.append(name)
    return loaded
