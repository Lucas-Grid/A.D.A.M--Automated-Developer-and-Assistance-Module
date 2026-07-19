"""Offline tests for the tool registry + every registered tool's run() path.

No network. High-danger desktop actions are exercised in DECLINED mode only;
the harmless desktop_move is exercised live (no system side effects beyond a
cursor move). git_commit is asserted to behave correctly given repo state.
"""
import os
import tempfile
import shutil

from jarvis.tools import register_default_tools
from jarvis.tools.registry import ToolContext
from jarvis.memory import Memory


def _ctx(allow=True):
    ws = tempfile.mkdtemp()
    return ws, ToolContext(
        workspace=ws,
        memory=Memory(db_path=os.path.join(ws, "m.db")),
        ask_confirm=(lambda p: allow),
    )


def test_registry_has_expected_tools():
    reg = register_default_tools(use_docker=False)
    names = reg.names()
    for required in (
        "file_list", "file_read", "file_write", "edit_file", "run_shell",
        "run_tests", "git_commit", "init_project", "web_search", "sandbox_exec",
        "memory_store", "memory_recall", "build_project", "screen_capture",
        "screen_understand", "desktop_move", "recall_semantic", "remember_semantic",
    ):
        assert required in names, f"missing tool: {required}"


def test_all_tools_return_toolresult():
    reg = register_default_tools(use_docker=False)
    ws, ctx = _ctx(allow=True)
    ctx_no = ToolContext(workspace=ws, memory=ctx.memory, ask_confirm=lambda p: False)
    calls = [
        ("file_list", ctx, {}),
        ("file_read", ctx, {"path": __file__}),
        ("file_write", ctx, {"path": os.path.join(ws, "t.txt"), "content": "hi"}),
        ("edit_file", ctx, {"path": os.path.join(ws, "n.py"), "content": "print(1)\n"}),
        ("run_shell", ctx, {"command": "echo ok"}),
        ("run_tests", ctx, {"cwd": ws}),
        ("memory_store", ctx, {"key": "k", "value": "v"}),
        ("memory_recall", ctx, {"key": "k"}),
        ("web_search", ctx, {"query": "python"}),
        ("sandbox_exec", ctx, {"code": "print(7)"}),
        ("init_project", ctx, {"name": "dp", "language": "python", "description": "x"}),
        ("git_commit", ctx, {"message": "t", "cwd": "dp"}),
        ("remember_semantic", ctx, {"text": "fact", "collection": "facts"}),
        ("recall_semantic", ctx, {"query": "fact", "collection": "facts"}),
        ("speak", ctx, {"text": "hi"}),
        ("desktop_move", ctx, {"x": 300, "y": 300}),
        ("screen_capture", ctx, {}),
        ("screen_understand", ctx, {}),
        ("app_launch", ctx_no, {"target": "notepad"}),
        ("desktop_click", ctx_no, {"x": 1, "y": 1}),
        ("desktop_type", ctx_no, {"text": "x"}),
        ("desktop_hotkey", ctx_no, {"keys": "ctrl,s"}),
        ("meta_create_tool", ctx_no, {"name": "foo", "description": "bar",
                                       "body": "return ToolResult(ok=True, output='x', tool='foo')"}),
    ]
    for name, c, kw in calls:
        r = reg.get(name).run(c, **kw)
        assert hasattr(r, "ok") and hasattr(r, "output"), f"{name} did not return ToolResult"
    shutil.rmtree(ws, ignore_errors=True)


def test_edit_file_creates_new_file():
    reg = register_default_tools(use_docker=False)
    ws, ctx = _ctx(allow=True)
    p = os.path.join(ws, "created.py")
    r = reg.get("edit_file").run(ctx, path="created.py", content="x = 1\n")
    assert r.ok, r.error
    assert os.path.isfile(p)
    assert open(p).read() == "x = 1\n"
    shutil.rmtree(ws, ignore_errors=True)


def test_git_commit_on_clean_repo_is_honest():
    """init_project already commits; a second commit with no changes should
    report the real git state, not pretend success."""
    reg = register_default_tools(use_docker=False)
    ws, ctx = _ctx(allow=True)
    reg.get("init_project").run(ctx, name="dp", language="python", description="x")
    r = reg.get("git_commit").run(ctx, message="noop", cwd="dp")
    # git exits 1 with 'nothing to commit' — the message lands in output
    assert (not r.ok) and "nothing to commit" in (r.output or ""), (r.error, r.output)
    shutil.rmtree(ws, ignore_errors=True)
