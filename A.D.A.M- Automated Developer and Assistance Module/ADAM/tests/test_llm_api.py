"""Tests for LLM API endpoints."""
import os

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.core.app import create_app
from ADAM.core.config import reset_settings
from ADAM.llm.router import LLMRouter


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("ADAM_DB_PATH", str(db))
    reset_settings()
    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_llm_models_endpoint_default(client):
    resp = client.get("/api/v1/llm/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
