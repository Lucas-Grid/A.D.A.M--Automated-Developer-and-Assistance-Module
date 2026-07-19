"""Tests for the FastAPI server wiring. Prefers starlette.testclient when
available; otherwise just asserts the app and routes were built."""
import os
import tempfile
import shutil
import importlib.util

from jarvis.server import build_app


def _have_testclient():
    return importlib.util.find_spec("starlette.testclient") is not None


def test_app_builds_with_routes():
    # build_app() constructs its own provider/registry/memory from config and
    # falls back to the local provider when no key is present.
    app = build_app()
    paths = {r.path for r in app.routes}
    for required in ("/health", "/tools", "/ask", "/ask_full", "/memory",
                     "/recall_semantic", "/speak"):
        assert required in paths, f"missing route {required}"


def test_health_and_tools_endpoints():
    if not _have_testclient():
        return  # skip live HTTP if TestClient unavailable
    from starlette.testclient import TestClient

    app = build_app()
    client = TestClient(app)
    h = client.get("/health")
    assert h.status_code == 200 and h.json().get("status") == "ok"
    t = client.get("/tools")
    assert t.status_code == 200 and isinstance(t.json(), list)


def test_ask_and_semantic_and_speak_endpoints():
    if not _have_testclient():
        return
    from starlette.testclient import TestClient

    app = build_app()
    client = TestClient(app)
    # /ask dispatches a tool through the HTTP loop (local provider offline)
    a = client.post("/ask", json={"message": "run this python: print(21 * 2)"})
    assert a.status_code == 200 and "42" in a.json().get("answer", "")
    # /recall_semantic returns a results list (empty is fine)
    r = client.post("/recall_semantic", json={"query": "anything", "collection": "default"})
    assert r.status_code == 200 and "results" in r.json()
    # /speak is a graceful no-op without a TTS key
    s = client.post("/speak", json={"text": "hello"})
    assert s.status_code == 200 and s.json().get("ok") in (True, False)
