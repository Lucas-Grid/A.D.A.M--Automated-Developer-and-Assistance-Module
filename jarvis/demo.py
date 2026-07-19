"""End-to-end smoke test for the Jarvis agent loop using the local provider.

Run:  python -m jarvis.demo
No API key or network required -- it proves plan -> act -> observe -> answer.
"""
from __future__ import annotations

from jarvis.config import load_config
from jarvis.memory import Memory
from jarvis.orchestrator import Orchestrator
from jarvis.providers.registry import build_providers, get_provider
from jarvis.tools import register_default_tools

SCENARIOS = [
    "run this python: ```python\nprint('2 ** 10 =', 2 ** 10)\n```",
    "list files",
    "remember db_host = localhost:5432",
    "recall db_host",
    "search for FastAPI async tutorial",
]


def main() -> None:
    cfg = load_config()
    providers = build_providers(cfg)
    prov = providers.get(cfg.default_provider) or get_provider()
    reg = register_default_tools(use_docker=False)
    mem = Memory(db_path=":memory:")  # ephemeral for the demo
    orch = Orchestrator(
        provider=prov,
        registry=reg,
        memory=mem,
        max_steps=cfg.max_steps,
        require_confirmation=False,
        workspace=".",
    )
    print(f"=== Jarvis demo | provider={orch.provider.name} model={orch.provider.model} ===\n")
    for i, sc in enumerate(SCENARIOS, 1):
        orch.short.clear()  # each scenario is a fresh turn
        print(f"\n----- Scenario {i}: {sc!r} -----")
        answer = orch.chat(sc, verbose=True)
        print(f"<<< FINAL ANSWER >>>\n{answer}\n")
    print("=== Demo complete ===")


if __name__ == "__main__":
    main()
