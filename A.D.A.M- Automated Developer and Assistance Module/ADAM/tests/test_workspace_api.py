"""Tests for workspace API endpoints."""
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.core.app import create_app
from ADAM.workspace.manager import WorkspaceManager


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    from ADAM.workspace.manager import reset_workspace_manager
    from ADAM.memory.store import reset_memory
    reset_settings()
    reset_workspace_manager()
    reset_memory()
    import os
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_register_and_list_workspace(client):
    resp = client.post("/api/v1/workspaces/", params={"name": "ws1", "path": "C:/fake", "description": "demo"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "ws1"

    resp = client.get("/api/v1/workspaces/")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_set_active_and_memory(client):
    client.post("/api/v1/workspaces/", params={"name": "ws1", "path": "C:/fake"})
    resp = client.post("/api/v1/workspaces/active/ws1")
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] == 1

    resp = client.get("/api/v1/workspaces/active")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "ws1"
