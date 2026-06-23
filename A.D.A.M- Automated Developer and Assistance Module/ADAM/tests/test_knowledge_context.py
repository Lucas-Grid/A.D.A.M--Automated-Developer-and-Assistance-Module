"""Tests for knowledge context engine."""
import os

import pytest

from ADAM.automations.history import JobHistory, reset_job_history
from ADAM.knowledge.context import ContextEngine, get_context_engine, reset_context_engine
from ADAM.knowledge.graph import Entity, EntityStore, get_entity_store, reset_entity_store
from ADAM.knowledge.memory import KnowledgeMemory, get_knowledge_memory, reset_knowledge_memory
from ADAM.knowledge.queries import get_query_engine, reset_query_engine
from ADAM.memory.store import get_memory, reset_memory


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_entity_store()
    reset_query_engine()
    reset_context_engine()
    reset_job_history()
    reset_memory()
    reset_knowledge_memory()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))


def test_build_context_missing_entity(env):
    engine = get_context_engine()
    context = engine.build_context("missing")
    assert "error" in context


def test_build_context_with_relationships(env):
    store = get_entity_store()
    store.add_entity(Entity(entity_id="e1", type="workspace", name="WS"))
    store.add_entity(Entity(entity_id="e2", type="model", name="Model"))
    store.add_relationship("e1", "e2", "USES")

    engine = get_context_engine()
    context = engine.build_context("e1")
    assert context["entity"]["entity_id"] == "e1"
    assert len(context["related"]) == 1
    assert context["related"][0]["entity"]["entity_id"] == "e2"
