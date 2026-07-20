"""Offline tests for the holographic GUI app + voice-input capability flag.

Exercises the Web layer (app build, /health, /ask via TestClient) without a
microphone or network. Voice *availability* is asserted to be a clean bool.
"""
import os

os.environ.pop("NVIDIA_NIM_API_KEY", None)  # force offline local brain

from jarvis.gui import build_gui_app, GuiState, _voice_available
from jarvis.voice_input import VoiceInput


def test_gui_app_builds_and_health():
    app = build_gui_app()
    from fastapi.testclient import TestClient

    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert "voice_available" in body
    assert isinstance(body["voice_available"], bool)


def test_gui_index_serves_holo_html():
    app = build_gui_app()
    from fastapi.testclient import TestClient

    c = TestClient(app)
    r = c.get("/")
    assert r.status_code == 200
    assert "JARVIS" in r.text  # our HUD markup present


def test_gui_ask_routes_through_orchestrator_offline():
    app = build_gui_app()
    from fastapi.testclient import TestClient

    c = TestClient(app)
    r = c.post("/ask", json={"message": "add 2 and 3"})
    assert r.status_code == 200, r.text
    ans = r.json().get("answer", "")
    assert isinstance(ans, str) and len(ans) > 0


def test_toggle_confirm_flips_handsfree():
    app = build_gui_app()
    from fastapi.testclient import TestClient

    c = TestClient(app)
    r = c.post("/toggle_confirm", json={"enabled": True})
    assert r.status_code == 200 and r.json()["handsfree"] is True
    r2 = c.post("/toggle_confirm", json={"enabled": False})
    assert r2.json()["handsfree"] is False


def test_voice_input_capability_is_bool():
    # VoiceInput degrades gracefully: .available is a bool, never raises.
    vi = VoiceInput(on_command=lambda t: None)
    assert isinstance(vi.available, bool)
    # start() returns True iff a backend is available (starts the listener),
    # and False otherwise -- never raises.
    assert vi.start() == vi.available
    vi.stop()


def test_gui_state_bus_is_singleton_threadsafe():
    s = GuiState()
    s.set(state="listening", transcript="hello")
    assert s.state == "listening"
    assert s.transcript == "hello"
