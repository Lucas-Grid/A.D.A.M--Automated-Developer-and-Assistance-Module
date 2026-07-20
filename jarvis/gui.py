"""Holographic Jarvis GUI launcher + shared real-time state bus.

This wires the three new "desktop assistant" pillars together:

  * a self-contained holographic HTML/CSS/Canvas HUD (jarvis/gui/holo.html)
    with an animated, interactive pulse that reacts to Jarvis' state
    (idle / listening / thinking / speaking);
  * a WebSocket bridge (/ws) streaming that state + live transcript to the HUD;
  * optional voice input (jarvis.voice_input.VoiceInput) so Jarvis is driven
    by the user's voice (wake word "Jarvis" or hands-free), routing recognized
    speech straight into the orchestrator / desktop tools;
  * screen perception is already in the toolset (screen_capture /
    screen_understand); the GUI adds a /screen endpoint to surface the latest
    capture.

The GUI runs its own FastAPI app (separate from the headless server.py) so
`python -m jarvis gui` is a single command that boots the assistant + HUD.

State bus: a tiny module-level singleton (GuiState) so the voice thread and the
orchestrator hook can push updates without coupling.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from jarvis.config import load_config, effective_default_provider
from jarvis.memory import Memory
from jarvis.orchestrator import Orchestrator
from jarvis.providers.registry import build_providers, get_provider
from jarvis.tools import register_default_tools
from jarvis.tools.registry import ToolRegistry


# --------------------------------------------------------------------------
# Real-time state bus (singleton, thread-safe)
# --------------------------------------------------------------------------
class GuiState:
    def __init__(self) -> None:
        self.state = "idle"          # idle|listening|thinking|speaking
        self.transcript = ""
        self.energy = 0.0
        self.handsfree = False
        self.mic_on = False
        self.model = ""              # active provider name (model selector)
        self.model_id = ""           # active model id
        self._clients: set[WebSocket] = set()
        self._lock = threading.Lock()

    def set(self, **kw: Any) -> None:
        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self._broadcast()

    def push(self, msg: dict[str, Any]) -> None:
        self._broadcast(msg)

    def _broadcast(self, msg: Optional[dict[str, Any]] = None) -> None:
        if msg is None:
            msg = {
                "type": "state",
                "state": self.state,
                "transcript": self.transcript,
                "energy": self.energy,
                "model": self.model,
                "model_id": self.model_id,
            }
        data = json.dumps(msg)
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                asyncio.run_coroutine_threadsafe(ws.send_text(data), _LOOP)
            except Exception:
                dead.append(ws)
        for d in dead:
            self._clients.discard(d)


GUI_STATE = GuiState()
_LOOP: Optional[asyncio.AbstractEventLoop] = None


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
def build_gui_app(autostart_voice: bool = True) -> FastAPI:
    cfg = load_config()
    providers = build_providers(cfg)
    default_name = effective_default_provider(cfg)
    prov = providers.get(default_name) or get_provider()
    reg = register_default_tools(ToolRegistry(), use_docker=bool(cfg.sandbox.get("use_docker")))
    mem = Memory(db_path=cfg.memory.get("db_path", "jarvis_memory.db"))
    orch = Orchestrator(
        provider=prov, registry=reg, memory=mem,
        max_steps=cfg.max_steps, require_confirmation=True, workspace=cfg.workspace,
    )

    app = FastAPI(title="Jarvis Holographic GUI", version="0.1.0")
    # Stash the built providers + config on the orchestrator so the model
    # selector endpoints can swap the active provider live (no restart).
    orch._providers = providers  # type: ignore[attr-defined]
    orch._cfg = cfg  # type: ignore[attr-defined]
    _mount(app, orch, cfg)
    if autostart_voice:
        _autostart_voice(orch)
    return app


def _mount(app: FastAPI, orch: Orchestrator, cfg) -> None:
    gui_dir = os.path.dirname(__file__)
    holo_path = os.path.join(gui_dir, "gui", "holo.html")
    html = ""
    try:
        with open(holo_path, "r", encoding="utf-8") as fh:
            html = fh.read()
    except Exception:
        html = "<h1>holo.html missing</h1>"

    # Serve the bundled SiriWave library (and any other gui assets) offline,
    # so the HUD needs no CDN.
    from fastapi.staticfiles import StaticFiles

    app.mount("/gui-assets", StaticFiles(directory=os.path.join(gui_dir, "gui")),
              name="gui-assets")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return html

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        global _LOOP
        _LOOP = asyncio.get_event_loop()
        await ws.accept()
        GUI_STATE._clients.add(ws)
        await ws.send_text(json.dumps({
            "type": "state", "state": GUI_STATE.state,
            "transcript": GUI_STATE.transcript, "energy": GUI_STATE.energy,
        }))
        try:
            while True:
                await ws.receive_text()  # keep-alive / ignore client msgs
        except WebSocketDisconnect:
            GUI_STATE._clients.discard(ws)
        except Exception:
            GUI_STATE._clients.discard(ws)

    @app.post("/ask")
    async def ask(request: Request):
        body = await request.json()
        message = (body or {}).get("message", "")
        if not message.strip():
            return JSONResponse({"error": "message required"}, status_code=400)
        GUI_STATE.set(state="thinking", transcript=message)
        answer = orch.chat(message, verbose=False)
        GUI_STATE.set(state="speaking", transcript=answer)
        # speak if TTS available; never blocks
        try:
            orch.voice.speak(answer)
        except Exception:
            pass
        GUI_STATE.set(state="idle")
        return {"answer": answer}

    @app.post("/listen")
    async def listen(request: Request):
        body = await request.json()
        on = bool((body or {}).get("on", False))
        mode = (body or {}).get("mode", "wake")
        if on:
            _start_voice(orch, mode)
            GUI_STATE.set(mic_on=True, state="listening")
        else:
            _stop_voice()
            GUI_STATE.set(mic_on=False, state="idle")
        return {"mic_on": GUI_STATE.mic_on}

    @app.post("/toggle_confirm")
    async def toggle_confirm(request: Request):
        body = await request.json()
        enabled = bool((body or {}).get("enabled", False))
        orch.require_confirmation = not enabled  # hands-free => auto-confirm
        GUI_STATE.set(handsfree=enabled)
        return {"handsfree": enabled}

    @app.get("/models")
    def models() -> dict:
        """List every selectable model across the user's providers (API keys).

        Returns a flat list of {provider, model, label} so the HUD can offer
        per-model selection, not just per-provider.
        """
        from jarvis.providers.registry import discover_models

        discovered = discover_models()
        current = GUI_STATE.model_id or GUI_STATE.model or orch.provider.model
        entries = []
        for prov, models in discovered.items():
            for m in (models or [prov]):
                entries.append({"provider": prov, "model": m,
                                "label": f"{m}  ·  {prov}"})
        return {"current": current, "models": entries}

    @app.post("/select_model")
    async def select_model(request: Request):
        body = await request.json()
        name = (body or {}).get("provider") or (body or {}).get("name")
        model_id = (body or {}).get("model")
        if not name:
            return JSONResponse({"error": "provider required"}, status_code=400)
        prov = getattr(orch, "_providers", {}).get(name)
        if prov is None and name == "local":
            from jarvis.providers.local import LocalProvider

            prov = LocalProvider()
        if prov is None:
            return JSONResponse({"error": f"unknown provider: {name}"}, status_code=404)
        # Allow picking a specific model id within the provider.
        if model_id and model_id != getattr(prov, "model", None):
            try:
                prov = type(prov)(model=model_id,
                                 base_url=getattr(prov, "base_url", None),
                                 api_key=getattr(prov, "api_key", None),
                                 vendor=getattr(prov, "vendor", None),
                                 cache=getattr(prov, "cache", None),
                                 **getattr(prov, "kwargs", {}))
            except Exception:
                pass  # fall back to provider's default model
        orch.provider = prov
        GUI_STATE.set(model=name, model_id=getattr(prov, "model", ""))
        return {"provider": name, "model": getattr(prov, "model", "")}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "provider": orch.provider.name,
                "voice_available": _voice_available(), "state": GUI_STATE.state}


# --------------------------------------------------------------------------
# Voice wiring
# --------------------------------------------------------------------------
_voice: Optional[Any] = None


def _voice_available() -> bool:
    try:
        from jarvis.voice_input import VoiceInput
        return VoiceInput(lambda _: None).available
    except Exception:
        return False


def _start_voice(orch: Orchestrator, mode: str) -> None:
    global _voice
    if _voice is not None:
        _voice.stop()
        _voice = None
    from jarvis.voice_input import VoiceInput

    def on_command(text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        GUI_STATE.set(state="thinking", transcript=text)
        try:
            answer = orch.chat(text, verbose=False)
        except Exception as e:
            answer = f"(error: {e})"
        GUI_STATE.set(state="speaking", transcript=answer)
        try:
            orch.voice.speak(answer)
        except Exception:
            pass
        GUI_STATE.set(state="idle")

    vi = VoiceInput(on_command=on_command)
    if not vi.available:
        GUI_STATE.push({"type": "transcript",
                        "text": "(voice input not installed: pip install vosk + model)"})
        return
    vi.set_mode(mode)
    vi.start()
    _voice = vi


def _stop_voice() -> None:
    global _voice
    if _voice is not None:
        _voice.stop()
        _voice = None


def _autostart_voice(orch: Orchestrator) -> None:
    """If a voice backend is present, begin continuous listening on launch so
    Jarvis responds to voice out of the box (say 'Jarvis' wake word, or full
    hands-free if enabled)."""
    try:
        from jarvis.voice_input import VoiceInput

        if VoiceInput(lambda _: None).available:
            _start_voice(orch, "wake")
            GUI_STATE.set(mic_on=True, state="listening")
    except Exception:
        pass


def main() -> None:
    import uvicorn

    app = build_gui_app()
    port = int(os.environ.get("JARVIS_GUI_PORT", "8000"))
    print(f"[jarvis] holographic GUI at  http://127.0.0.1:{port}")
    print("[jarvis] voice input available:", _voice_available())
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
