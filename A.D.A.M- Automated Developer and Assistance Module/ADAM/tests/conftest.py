"""Shared pytest fixtures."""
import sys
from pathlib import Path

import pytest

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Use an isolated SQLite database for tests."""
    from ADAM.core.config import reset_settings
    reset_settings()
    db = tmp_path / "test.db"
    monkeypatch.setenv("ADAM_DB_PATH", str(db))
    yield db
