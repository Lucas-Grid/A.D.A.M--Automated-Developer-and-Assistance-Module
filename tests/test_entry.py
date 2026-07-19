"""Tests for packaging / entry points / plugin loading.

No network. Verifies the project is shippable: `python -m jarvis` entry
exists, the example config parses, and YAML-declared plugins load.
"""
import os

import jarvis
from jarvis.cli import main as cli_main
from jarvis.config import load_config
from jarvis.tools import register_default_tools


def test_package_version():
    assert jarvis.__version__


def test_main_entry_is_callable():
    # `python -m jarvis` and the `jarvis` console script both resolve here.
    assert callable(cli_main)


def test_example_config_parses():
    here = os.path.dirname(os.path.abspath(__file__))
    example = os.path.join(here, "..", "jarvis", ".jarvis.example.yaml")
    # _load_dict returns the RAW parsed config (env: refs NOT yet expanded),
    # which is what proves secrets stay out of the file.
    from jarvis.config import _load_dict
    raw = _load_dict(os.path.abspath(example))
    names = [p["name"] for p in raw["providers"]]
    assert "nim" in names and "ollama" in names
    assert raw["default_provider"] == "nim"
    nim = next(p for p in raw["providers"] if p["name"] == "nim")
    assert str(nim["api_key"]).startswith("env:")


def test_plugin_loads_from_tools_plugins():
    reg = register_default_tools(use_docker=False)
    # the shipped demo plugin registers weather_lookup
    assert "weather_lookup" in reg.names(), "plugin did not load"
