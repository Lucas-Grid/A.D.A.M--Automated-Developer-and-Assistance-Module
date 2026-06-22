"""Tests for workspace memory integration."""
import json

import pytest

from ADAM.workspace.memory import WorkspaceMemory


@pytest.fixture()
def wmemory(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    from ADAM.memory.store import reset_memory
    reset_settings()
    reset_memory()
    import os
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    return WorkspaceMemory()


def test_save_and_load(wmemory):
    analysis = {
        "languages": ["Python"],
        "frameworks": ["FastAPI"],
        "dependency_files": ["pyproject.toml"],
        "project_size_bytes": 1234,
        "file_count": 10,
        "directory_count": 2,
    }
    wmemory.save_current("my-workspace", analysis)
    loaded = wmemory.load_current()
    assert loaded["current_workspace"] == "my-workspace"
    summary = loaded["summary"]
    assert summary["languages"] == ["Python"]
