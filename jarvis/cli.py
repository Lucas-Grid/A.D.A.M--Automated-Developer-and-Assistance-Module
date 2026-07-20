"""Interactive CLI for Jarvis."""
from __future__ import annotations

import sys
import os

from jarvis.config import load_config, effective_default_provider
from jarvis.memory import Memory
from jarvis.orchestrator import Orchestrator
from jarvis.providers.registry import build_providers
from jarvis.tools import register_default_tools


def _confirm_cli(prompt: str) -> bool:
    try:
        ans = input(f"  [confirm] {prompt}? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes")


def _run_tests() -> None:
    """Run the committed stdlib test suite (tests/run_tests.py)."""
    here = os.path.dirname(os.path.abspath(__file__))
    suite = os.path.join(here, "..", "tests", "run_tests.py")
    if not os.path.isfile(suite):
        print("Test suite not found at", suite)
        return
    print("Running Jarvis test suite...\n")
    rc = os.system(f'{sys.executable} "{os.path.abspath(suite)}"')
    print("\nTest suite exited with code", rc >> 8)


def build_orchestrator(cfg) -> Orchestrator:
    providers = build_providers(cfg)
    # Offline-first: if the configured default provider needs a key that isn't
    # present, fall back to the always-available local brain so Jarvis works
    # out of the box with no API key (and doesn't burn steps on 401 retries).
    default_name = effective_default_provider(cfg)
    if default_name != cfg.default_provider:
        print(
            f"[jarvis] no credential for default provider '{cfg.default_provider}'; "
            f"using '{default_name}' (offline brain). Set the API key + "
            f"default_provider in .jarvis.yaml to use a real model."
        )
    prov = providers.get(default_name)
    if prov is None:
        from jarvis.providers.registry import get_provider

        prov = get_provider()
    use_docker = bool(cfg.sandbox.get("use_docker"))
    reg = register_default_tools(use_docker=use_docker)
    mem = Memory(db_path=cfg.memory.get("db_path", "jarvis_memory.db"))
    return Orchestrator(
        provider=prov,
        registry=reg,
        memory=mem,
        max_steps=cfg.max_steps,
        require_confirmation=cfg.require_confirmation,
        workspace=cfg.workspace,
        ask_confirm=_confirm_cli,
    )


def main() -> None:
    cfg = load_config()
    orch = build_orchestrator(cfg)
    print(f"\nJARVIS v0.1  | provider={orch.provider.name} model={orch.provider.model}")
    print("Type a request, or 'help', 'tools', 'exit'. (Local provider needs no API key.)\n")
    while True:
        try:
            user = input("jarvis> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user:
            continue
        if user in ("exit", "quit"):
            print("Goodbye.")
            break
        if user == "help":
            print("Examples:")
            print("  run this python: ```python\nprint(2**10)\n```")
            print("  list files")
            print("  remember db_host = localhost")
            print("  recall db_host")
            print("  search for FastAPI tutorials")
            continue
        if user == "tools":
            for t in orch.registry.all():
                print(f"  - {t.name} [{t.danger}]: {t.description}")
            continue
        if user == "test":
            _run_tests()
            continue
        if user.startswith("build "):
            prompt = user[len("build "):].strip()
            if not prompt:
                print("Usage: build <what to build>")
                continue
            ctx = ToolContext(workspace=cfg.workspace, ask_confirm=_confirm_cli)
            builder = orch.registry.get("build_project")
            res = builder.run(ctx, prompt=prompt)
            print(f"\n[build_project] ok={res.ok}")
            print(res.output)
            continue
        orch.chat(user)


if __name__ == "__main__":
    main()
