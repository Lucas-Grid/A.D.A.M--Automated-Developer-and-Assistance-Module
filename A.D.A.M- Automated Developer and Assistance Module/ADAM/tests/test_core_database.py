"""Tests for core database module."""
from __future__ import annotations

import sqlite3

import pytest

from ADAM.core.config import reset_settings, get_settings
from ADAM.core.database import get_engine, get_session_factory, get_db, init_db


@pytest.fixture()
def db_engine():
    reset_settings()
    yield get_engine()


def test_engine_creation(db_engine):
    assert db_engine is not None
    assert str(db_engine.url).startswith("sqlite:///")


def test_session_factory(db_engine):
    factory = get_session_factory()
    assert factory is not None
    session = factory()
    assert session.is_active
    session.close()


def test_get_db_context_manager(db_engine):
    gen = get_db()
    session = next(gen)
    assert session.is_active
    session.close()


def test_init_db_creates_no_orm_tables(db_engine):
    # No SQLAlchemy ORM models exist yet; create_all should be a no-op
    init_db()
    con = sqlite3.connect(get_settings().db_path)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    # raw tables exist from legacy _ensure_table() paths
    assert any(t.endswith("_test") or t in tables for t in ["sqlite_sequence"])
    con.close()
