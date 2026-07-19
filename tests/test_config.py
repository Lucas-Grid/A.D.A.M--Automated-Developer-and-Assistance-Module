"""Tests for config loading + provider selection."""
import os
import tempfile
import shutil

from jarvis.config import load_config
from jarvis.cli import build_orchestrator

PROJECT_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jarvis", ".jarvis.yaml",
)


def test_config_parses_with_nim_default():
    cfg = load_config(PROJECT_CONFIG)
    names = [s.name for s in cfg.providers]
    assert "nim" in names
    assert "nim_oss120b" in names
    assert cfg.default_provider == "nim"
    oss = next(s for s in cfg.providers if s.name == "nim_oss120b")
    assert oss.enabled is False
    assert "gpt-oss-120b" in oss.model


def test_cli_selects_configured_default_provider():
    cfg = load_config(PROJECT_CONFIG)
    orch = build_orchestrator(cfg)
    # provider.model is the real signal of which provider was selected
    assert orch.provider.model == "stepfun-ai/step-3.7-flash"
