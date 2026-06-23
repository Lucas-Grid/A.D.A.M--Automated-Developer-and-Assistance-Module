"""Tests for agent API endpoints."""
import os

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.core.app import create_app
from ADAM.skills.engine import get_skill_engine
from ADAM.core.config import reset_settings, get_settings
from ADAM.agents.registry import reset_agent_registry


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("ADAM_DB_PATH", str(db))
    reset_settings()
    reset_agent_registry()
    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_create_agent_via_api(client):
    payload = {
        "id": "api-agent-1",
        "name": "API Test Agent",
        "role": "assistant",
        "description": "Test",
        "model_id": None,
        "enabled": True,
        "metadata": {},
    }
    resp = client.post("/api/v1/agents/", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True


def test_list_agents_via_api(client):
    resp = client.get("/api/v1/agents/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True


def test_enable_disable_agent_via_api(client):
    engine = get_skill_engine()
    engine.execute("agent.create", {
        "id": "toggle-agent",
        "name": "Toggle",
        "role": "assistant",
        "enabled": False,
    })

    resp = client.post("/api/v1/agents/toggle-agent/enable")
    assert resp.status_code == 200

    resp = client.post("/api/v1/agents/toggle-agent/disable")
    assert resp.status_code == 200
