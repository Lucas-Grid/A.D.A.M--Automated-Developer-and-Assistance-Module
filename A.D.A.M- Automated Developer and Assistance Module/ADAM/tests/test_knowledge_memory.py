"""Tests for knowledge graph memory integration."""
import os

import pytest

from ADAM.knowledge.graph import Entity, EntityStore, get_entity_store, reset_entity_store
from ADAM.knowledge.memory import KnowledgeMemory, get_knowledge_memory, reset_knowledge_memory
from ADAM.knowledge.relationships import VALID_RELATIONSHIP_TYPES
from ADAM.memory.store import get_memory, reset_memory


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_entity_store()
    reset_knowledge_memory()
    reset_memory()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))


def test_entity_persists_to_memory(env):
    store = get_entity_store()
    entity = store.add_entity(Entity(entity_id="e1", type="project", name="P", metadata={"key": "value"}))

    memory = get_knowledge_memory()
    memory.record_entity(entity)

    raw = memory.get_entity_memory("e1")
    assert raw is not None
    assert raw["entity_id"] == "e1"
    assert raw["metadata"]["key"] == "value"
