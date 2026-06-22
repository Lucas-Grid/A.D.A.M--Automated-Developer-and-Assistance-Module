"""Tests for project registry."""
import pytest

from ADAM.core.registry import ProjectRegistry


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    from ADAM.core.registry import reset_project_registry
    reset_settings()
    reset_project_registry()
    import os
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    return ProjectRegistry()


def test_create_and_get(registry):
    p = registry.create("proj1", "C:/x/y", "desc", "model-a")
    assert p["name"] == "proj1"
    assert registry.get("proj1") is not None
