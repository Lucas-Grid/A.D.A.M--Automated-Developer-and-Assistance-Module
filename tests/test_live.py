"""Live LLM smoke test (OPTIONAL).

Only runs when NVIDIA_NIM_API_KEY is set. Exercises a few real end-to-end
turns against NVIDIA NIM to prove the wiring works on a real model. This is
NOT part of the offline suite. Run it explicitly (it auto-skips offline):

    python tests/run_tests.py test_live   # needs NVIDIA_NIM_API_KEY
"""
import os
import time
import tempfile
import shutil

HAVE_KEY = bool(os.environ.get("NVIDIA_NIM_API_KEY"))


def test_live_reasoning_and_tools():
    if not HAVE_KEY:
        print("test_live_reasoning_and_tools: SKIPPED (no NVIDIA_NIM_API_KEY)")
        return
    from jarvis.config import load_config
    from jarvis.orchestrator import Orchestrator
    from jarvis.memory import Memory
    from jarvis.providers.registry import build_providers
    from jarvis.tools import register_default_tools

    PROJECT_CONFIG = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "jarvis", ".jarvis.yaml",
    )
    cfg = load_config(PROJECT_CONFIG)
    providers = build_providers(cfg)
    ws = tempfile.mkdtemp()
    orch = Orchestrator(
        provider=providers["nim"],
        registry=register_default_tools(use_docker=False),
        memory=Memory(db_path=os.path.join(ws, "m.db")),
        max_steps=14, require_confirmation=False, workspace=ws,
    )
    ans = orch.chat("What is 2**10 + 7? Answer in one short sentence.", verbose=False)
    assert ans and "1031" in ans, ans
    ans = orch.chat("run this python: print('e2e', 2**10)", verbose=False)
    assert ans and "e2e 1024" in ans, ans
    orch.chat("remember_semantic: Jarvis live test ran on NVIDIA NIM", verbose=False)
    time.sleep(1)
    ans = orch.chat("What provider did the Jarvis live test run on?", verbose=False)
    assert ans and "NVIDIA NIM" in ans, ans
    shutil.rmtree(ws, ignore_errors=True)
