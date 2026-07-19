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
