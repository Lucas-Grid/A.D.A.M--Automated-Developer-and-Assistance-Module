"""Tests for core FastAPI application factory."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ADAM.core.app import create_app
from ADAM.core.config import reset_settings


@pytest.fixture()
def client():
    reset_settings()
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_health_endpoint(client):
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "status" in data["data"]


def test_info_endpoint(client):
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "name" in data["data"]


def test_routers_registered(client):
    response = client.get("/api/v1/skills/")
    assert response.status_code == 200
