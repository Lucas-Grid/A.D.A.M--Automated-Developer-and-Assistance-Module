"""Tests for model API endpoints."""
import os

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.core.app import create_app
from ADAM.connections.model_registry import ModelRegistry, reset_model_registry


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_model_registry()
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_list_models_empty(client):
    resp = client.get("/api/v1/models/")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["data"]["models"] == []


def test_register_and_select_model(client):
    # Pre-register a model directly
    registry = ModelRegistry()
    registry.register(
        {
            "model_id": "test-model",
            "provider": "ollama",
            "display_name": "Test",
            "local_or_remote": "local",
            "supports_chat": True,
        }
    )

    resp = client.get("/api/v1/models/")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["models"]) == 1

    resp = client.post("/api/v1/models/select?model_id=test-model")
    assert resp.status_code == 200
    assert resp.json()["data"]["result"]["selected"]["model_id"] == "test-model"
