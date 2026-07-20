"""Tests for the orchestrator agent loop using the deterministic local provider
(no network). Verifies: a final answer is returned, tool calls are parsed and
dispatched, and the loop terminates."""
import os
import tempfile
import shutil

from jarvis.orchestrator import Orchestrator
from jarvis.providers.local import LocalProvider
from jarvis.memory import Memory
from jarvis.tools import register_default_tools
from jarvis.tools.registry import ToolContext


def _orch(max_steps=6):
    ws = tempfile.mkdtemp()
    reg = register_default_tools(use_docker=False)
    orch = Orchestrator(
        provider=LocalProvider(),
        registry=reg,
        memory=Memory(db_path=os.path.join(ws, "m.db")),
        max_steps=max_steps,
        require_confirmation=False,
        workspace=ws,
    )
    return ws, orch


def test_local_loop_returns_answer():
    ws, orch = _orch()
    ans = orch.chat("run this python: print('hi')", verbose=False)
    assert ans and "hi" in ans, ans
    shutil.rmtree(ws, ignore_errors=True)


def test_local_loop_invokes_sandbox_tool():
    ws, orch = _orch()
    # exercise the code path that dispatches a tool and feeds back its result
    res = orch.ask_full("run this python: print(2 ** 8)", verbose=False)
    tr = res.get("tool_results", [])
    assert tr, "no tool results recorded"
    assert any("256" in (r.get("content") or "") for r in tr)
    shutil.rmtree(ws, ignore_errors=True)


def test_local_loop_respects_max_steps():
    ws, orch = _orch(max_steps=3)
    # nonsense input should still terminate and return a string
    ans = orch.chat("asdfqwer zxcv", verbose=False)
    assert isinstance(ans, str)
    shutil.rmtree(ws, ignore_errors=True)


def test_chat_stream_yields_full_answer():
    ws, orch = _orch()
    parts = list(orch.chat_stream("run this python: print('hi')", verbose=False))
    joined = "".join(parts)
    assert joined and "hi" in joined, joined
    # chat() (non-streaming wrapper) must equal the joined streamed answer.
    assert orch.chat("run this python: print('hi')", verbose=False) == joined
    shutil.rmtree(ws, ignore_errors=True)


def test_local_brain_build_scaffolds_runnable_project():
    """The local brain's offline 'build ...' must scaffold a real runnable app
    (init_project), not loop or silently no-op. Prove the artifact works."""
    import subprocess

    ws, orch = _orch()
    try:
        ans = orch.chat("build a tiny python app", verbose=False)
        assert "Created project" in ans, ans
        # Find the scaffolded dir and run its main.py to confirm it's runnable.
        made = None
        for d in os.listdir(ws):
            if os.path.isdir(os.path.join(ws, d)) and os.path.isfile(os.path.join(ws, d, "main.py")):
                made = d
                break
        assert made is not None, "no scaffolded project created"
        out = subprocess.run(f'python "{os.path.join(ws, made, "main.py")}"',
                              shell=True, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        assert "Hello from" in out.stdout, out.stdout
    finally:
        shutil.rmtree(ws, ignore_errors=True)
