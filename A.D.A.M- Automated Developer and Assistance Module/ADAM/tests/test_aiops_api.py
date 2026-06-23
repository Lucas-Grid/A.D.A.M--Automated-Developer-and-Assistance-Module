"""Tests for aiops API endpoints."""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.core.app import create_app


@pytest.fixture()
def client(monkeypatch):
    mock_provider = MagicMock()
    mock_provider.embed = AsyncMock(return_value=[0.1] * 8)
    mock_provider.embed_batch = AsyncMock(return_value=[[0.1] * 8])
    import ADAM.skills.aiops.skills as aiops_skills
    monkeypatch.setattr(aiops_skills, "get_embedding_provider", lambda name, **kwargs: mock_provider)

    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_vector_index_endpoint(client):
    resp = client.post("/api/v1/vector/index", json={"documents": ["hello world"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True


def test_vector_search_endpoint(client):
    resp = client.get("/api/v1/vector/search", params={"q": "hello", "top_k": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True


def test_context_build_endpoint(client):
    resp = client.post("/api/v1/vector/context/build", params={"query": "test", "top_k": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
