"""Tests for core configuration."""
from __future__ import annotations

import os

import pytest

from ADAM.core.config import get_settings, reset_settings


@pytest.fixture()
def settings():
    reset_settings()
    yield get_settings()


def test_settings_loads_from_env(settings):
    assert settings.app_name == "ADAM OS"
    assert settings.api_port == 8000


def test_settings_paths_are_pathlib(settings):
    assert hasattr(settings.db_path, "is_absolute") or isinstance(settings.db_path, type(settings.db_path))
    assert hasattr(settings.logs_dir, "is_absolute") or isinstance(settings.logs_dir, type(settings.logs_dir))


def test_settings_ollama_default(settings):
    assert settings.ollama_base_url == "http://localhost:11434"


def test_settings_api_keys_default_empty(settings):
    assert settings.openai_api_key == ""
    assert settings.openrouter_api_key == ""
