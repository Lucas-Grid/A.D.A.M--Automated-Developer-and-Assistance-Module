"""Tests for ECC API endpoints."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.core.app import create_app
from ADAM.core.config import reset_settings


@pytest.fixture()
def client(monkeypatch):
    db = tempfile.mktemp(suffix=".db")
    monkeypatch.setenv("ADAM_DB_PATH", db)
    reset_settings()
    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_ecc_plan_endpoint(client):
    resp = client.post("/api/v1/ecc/plan", json={"agent_id": "a", "objective": "search knowledge"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "data" in body


def test_ecc_validate_endpoint(client):
    resp = client.post("/api/v1/ecc/validate", json={
        "plan": {"agent_id": "a", "objective": "test", "goals": ["test"], "steps": [{"skill": "system.status"}]}
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
