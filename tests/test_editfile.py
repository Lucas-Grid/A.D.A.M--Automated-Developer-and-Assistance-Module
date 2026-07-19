"""Focused tests for edit_file: create vs edit, nested paths, content guard,
block replace, and declined confirmation."""
import os
import tempfile
import shutil

from jarvis.tools.coding import EditFileTool
from jarvis.tools.registry import ToolContext


def _ctx(allow=True, ws=None):
    ws = ws or tempfile.mkdtemp()
    return ws, ToolContext(workspace=ws, ask_confirm=lambda p: allow)


def test_create_new_file_with_content():
    ws, ctx = _ctx()
    p = os.path.join(ws, "a.py")
    r = EditFileTool().run(ctx, path="a.py", content="print(1)\n")
    assert r.ok, r.error
    assert open(p).read() == "print(1)\n"
    shutil.rmtree(ws, ignore_errors=True)


def test_create_nested_makes_dirs():
    ws, ctx = _ctx()
    r = EditFileTool().run(ctx, path="pkg/mod.py", content="y = 2\n")
    assert r.ok and os.path.isfile(os.path.join(ws, "pkg", "mod.py"))
    shutil.rmtree(ws, ignore_errors=True)


def test_refuse_create_without_content():
    ws, ctx = _ctx()
    r = EditFileTool().run(ctx, path="empty.py")
    assert (not r.ok) and "no content" in (r.error or "")
    assert not os.path.isfile(os.path.join(ws, "empty.py"))
    shutil.rmtree(ws, ignore_errors=True)


def test_edit_existing_full_overwrite():
    ws, ctx = _ctx()
    p = os.path.join(ws, "e.py")
    open(p, "w").write("OLD\n")
    r = EditFileTool().run(ctx, path="e.py", content="NEW\n")
    assert r.ok and open(p).read() == "NEW\n"
    shutil.rmtree(ws, ignore_errors=True)


def test_block_replace():
    ws, ctx = _ctx()
    p = os.path.join(ws, "b.py")
    open(p, "w").write("aaa bbb ccc\n")
    r = EditFileTool().run(ctx, path="b.py", old="bbb", new="ZZZ")
    assert r.ok and "ZZZ" in open(p).read()
    shutil.rmtree(ws, ignore_errors=True)


def test_declined_create_is_noop():
    ws, ctx = _ctx(allow=False)
    r = EditFileTool().run(ctx, path="nope.py", content="x\n")
    assert (not r.ok) and not os.path.isfile(os.path.join(ws, "nope.py"))
    shutil.rmtree(ws, ignore_errors=True)
