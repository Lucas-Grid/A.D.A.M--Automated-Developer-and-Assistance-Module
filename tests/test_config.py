"""Tests for config loading + provider selection."""
import os
import tempfile
import shutil

from jarvis.config import load_config, effective_default_provider
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
    # With a credential present, the CLI must select the configured NIM default.
    prev = os.environ.get("NVIDIA_NIM_API_KEY")
    os.environ["NVIDIA_NIM_API_KEY"] = "dummy-for-test"
    try:
        cfg = load_config(PROJECT_CONFIG)
        orch = build_orchestrator(cfg)
        # provider.model is the real signal of which provider was selected
        assert orch.provider.model == "stepfun-ai/step-3.7-flash"
    finally:
        if prev is None:
            os.environ.pop("NVIDIA_NIM_API_KEY", None)
        else:
            os.environ["NVIDIA_NIM_API_KEY"] = prev


def test_offline_first_falls_back_to_local_without_key():
    # When the configured default needs a missing key, effective_default_provider
    # must fall back to the always-available local brain (offline-first promise).
    prev = os.environ.pop("NVIDIA_NIM_API_KEY", None)
    try:
        cfg = load_config(PROJECT_CONFIG)
        assert cfg.default_provider == "nim"
        chosen = effective_default_provider(cfg)
        assert chosen == "local", chosen
        # And the orchestrator built without a key should actually use local.
        orch = build_orchestrator(cfg)
        assert orch.provider.name == "local", orch.provider.name
    finally:
        if prev is not None:
            os.environ["NVIDIA_NIM_API_KEY"] = prev


def test_load_config_falls_back_to_bundled_config():
    # From a directory with no ./jarvis.yaml and no JARVIS_CONFIG, load_config
    # must resolve the package-bundled jarvis/.jarvis.yaml (nim default),
    # NOT silently fall back to the bare local provider.
    import tempfile
    prev = os.environ.pop("JARVIS_CONFIG", None)
    cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    try:
        os.chdir(tmp)  # no ./jarvis.yaml here
        cfg = load_config()
        assert cfg.default_provider == "nim", cfg.default_provider
        assert any(s.name == "nim" for s in cfg.providers)
    finally:
        os.chdir(cwd)
        if prev is not None:
            os.environ["JARVIS_CONFIG"] = prev
