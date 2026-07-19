"""Tests for the layered memory store and the semantic (vector) memory."""
import os
import tempfile
import shutil

from jarvis.memory import Memory
from jarvis.vectormem import VectorMemory


def test_kv_store_recall():
    ws = tempfile.mkdtemp()
    m = Memory(db_path=os.path.join(ws, "m.db"))
    m.store("k", "v", scope="global")
    assert m.recall("k", scope="global") == "v"
    assert m.recall("missing", scope="global") is None
    shutil.rmtree(ws, ignore_errors=True)


def test_scoped_memory_isolation():
    ws = tempfile.mkdtemp()
    m = Memory(db_path=os.path.join(ws, "m.db"))
    m.store("token", "secret", scope="project")
    assert m.recall("token", scope="project") == "secret"
    assert m.recall("token", scope="global") is None
    shutil.rmtree(ws, ignore_errors=True)


def test_vectormem_collection_none_spans_all():
    ws = tempfile.mkdtemp()
    vm = VectorMemory(db_path=os.path.join(ws, "v.db"))
    vm.remember("uses NVIDIA NIM", collection="default")
    vm.remember("runs on step-3.7", collection="facts")
    # unscoped recall searches across all collections
    hits = vm.recall("nim", collection=None, top_k=5)
    assert hits, "expected at least the clearly-matching default fact"
    assert any("NIM" in h["text"] and h["collection"] == "default" for h in hits)
    # unscoped must return at least as much as a single-collection scoped recall
    scoped = vm.recall("nim", collection="default", top_k=5)
    assert len(hits) >= len(scoped)
    shutil.rmtree(ws, ignore_errors=True)


def test_vectormem_scoped_recall():
    ws = tempfile.mkdtemp()
    vm = VectorMemory(db_path=os.path.join(ws, "v.db"))
    vm.remember("uses NVIDIA NIM", collection="default")
    vm.remember("runs on step-3.7", collection="facts")
    def_hits = vm.recall("nim", collection="default", top_k=5)
    assert len(def_hits) >= 1 and "NIM" in def_hits[0]["text"]
    assert def_hits[0]["collection"] == "default"
    shutil.rmtree(ws, ignore_errors=True)
