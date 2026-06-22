"""Tests for memory store."""
import pytest

from ADAM.memory.store import MemoryStore


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    return MemoryStore()


def test_set_get(store):
    store.set("foo", "bar")
    result = store.get("foo")
    assert result is not None
    assert result["value"] == "bar"


def test_search(store):
    store.set("alpha", "hello world")
    store.set("beta", "goodbye world")
    results = store.search("world")
    assert len(results) == 2
