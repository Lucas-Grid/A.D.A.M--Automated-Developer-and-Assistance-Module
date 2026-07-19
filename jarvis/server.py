"""FastAPI server exposing Jarvis as an HTTP service.

Routes are registered individually (not via a shared APIRouter) to avoid the
known FastAPI 0.138.2 / Starlette 1.3.1 include_router bug that silently drops
routes. Each endpoint is added straight to the app. Body models are read
explicitly from the request to sidestep an environment-specific binding quirk.
"""
from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request

from jarvis.config import load_config
from jarvis.memory import Memory
from jarvis.orchestrator import Orchestrator
from jarvis.providers.registry import build_providers, get_provider
from jarvis.tools import register_default_tools
from jarvis.tools.registry import ToolRegistry


def build_app() -> FastAPI:
    cfg = load_config()
    providers = build_providers(cfg)
    prov = providers.get(cfg.default_provider) or get_provider()
    use_docker = bool(cfg.sandbox.get("use_docker"))
    # Fresh registry per app instance: the server must not inherit tools
    # registered into the process-global registry elsewhere (e.g. a meta-tool
    # generated in the same process). This keeps the served tool set fixed.
    reg = register_default_tools(ToolRegistry(), use_docker=use_docker)
    mem = Memory(db_path=cfg.memory.get("db_path", "jarvis_memory.db"))
    orch = Orchestrator(
        provider=prov,
        registry=reg,
        memory=mem,
        max_steps=cfg.max_steps,
        require_confirmation=False,  # server-side runs auto-confirm; CLI gates HITL
        workspace=cfg.workspace,
    )

    app = FastAPI(title="Jarvis Assistant API", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "provider": orch.provider.name, "model": orch.provider.model}

    @app.get("/tools")
    def tools():
        return [t.spec() for t in orch.registry.all()]

    @app.get("/memory")
    def memory_get(key: str = "", scope: str = ""):
        if key:
            return {"key": key, "scope": scope or None, "value": orch.memory.recall(key, scope=scope or None)}
        return {"memories": orch.memory.all(scope=scope or None)}

    @app.post("/recall_semantic")
    async def recall_semantic(request: Request):
        """Semantic memory search (folds ADAM vector store in)."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid JSON body")
        query = (body or {}).get("query", "")
        collection = (body or {}).get("collection", "default")
        top_k = int((body or {}).get("top_k", 5))
        if not query.strip():
            raise HTTPException(status_code=400, detail="query is required")
        hits = orch.vector.recall(query, collection=collection, top_k=top_k)
        return {"results": hits}

    @app.post("/speak")
    async def speak(request: Request):
        """Text-to-speech (folds ADAM voice in). Returns audio path/b64 or a graceful no-op."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid JSON body")
        text = (body or {}).get("text", "")
        if not text.strip():
            raise HTTPException(status_code=400, detail="text is required")
        return orch.voice.speak(text)

    @app.post("/ask")
    async def ask(request: Request):
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid JSON body")
        message = (body or {}).get("message", "")
        verbose = bool((body or {}).get("verbose", False))
        if not message.strip():
            raise HTTPException(status_code=400, detail="message is required")
        orch.short.clear()  # each HTTP request is a fresh turn
        answer = orch.chat(message, verbose=verbose)
        return {"answer": answer}

    @app.post("/ask_full")
    async def ask_full(request: Request):
        """OpenJarvis-style: content + tool_results + telemetry + tasks."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid JSON body")
        message = (body or {}).get("message", "")
        if not message.strip():
            raise HTTPException(status_code=400, detail="message is required")
        orch.short.clear()
        return orch.ask_full(message, verbose=False)

    return app


app = build_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
