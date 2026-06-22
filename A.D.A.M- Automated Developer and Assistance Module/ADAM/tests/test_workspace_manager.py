"""Tests for workspace manager."""
import pytest

from ADAM.core.exceptions import WorkspaceError
from ADAM.workspace.manager import WorkspaceManager


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    from ADAM.workspace.manager import reset_workspace_manager
    reset_settings()
    reset_workspace_manager()
    import os
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    return WorkspaceManager()


def test_register_and_get(manager):
    ws = manager.register("ws1", "C:/fake", "desc")
    assert ws["name"] == "ws1"
    assert manager.get("ws1") is not None


def test_set_active(manager):
    manager.register("ws1", "C:/fake")
    manager.register("ws2", "C:/fake2")
    active = manager.set_active("ws2")
    assert active["is_active"] == 1
    assert manager.get_active()["name"] == "ws2"


def test_list_and_delete(manager):
    manager.register("ws1", "C:/fake")
    manager.register("ws2", "C:/fake2")
    assert len(manager.list_workspaces()) == 2
    manager.delete("ws1")
    assert len(manager.list_workspaces()) == 1
