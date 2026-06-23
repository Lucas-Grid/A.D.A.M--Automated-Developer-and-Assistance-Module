"""Tests for trigger system."""
import pytest

from ADAM.automations.triggers import (
    FileSystemTrigger,
    ManualTrigger,
    StartupTrigger,
    TriggerManager,
)


def test_startup_trigger_fires_on_startup():
    t = StartupTrigger({})
    assert t.should_fire({"event": "startup"}) is True
    assert t.should_fire({"event": "manual"}) is False


def test_manual_trigger_fires_on_manual():
    t = ManualTrigger({})
    assert t.should_fire({"event": "manual"}) is True
    assert t.should_fire({"event": "startup"}) is False


def test_filesystem_trigger_requires_event():
    t = FileSystemTrigger({"path": ".", "patterns": ["*"]})
    assert t.should_fire({"event": "filesystem"}) is True
    assert t.should_fire({"event": "manual"}) is False


def test_trigger_manager_register_and_evaluate():
    mgr = TriggerManager()
    t = mgr.register("manual", {})
    assert t is not None
    assert mgr.evaluate("manual", {"event": "manual"}) is True
    assert mgr.evaluate("startup", {"event": "manual"}) is False


def test_trigger_manager_unsupported_type_raises():
    mgr = TriggerManager()
    with pytest.raises(ValueError):
        mgr.register("unknown", {})

    assert mgr.evaluate("unknown", {}) is False
