"""LLM API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from ADAM.llm.router import LLMRouter
from ADAM.llm.telemetry import LLMTelemetry
from ADAM.llm.types import ChatMessage
from ADAM.skills.engine import get_skill_engine
from ADAM.core.types import ResponseModel

router = APIRouter()


@router.post("/chat", response_model=ResponseModel)
async def chat(payload: dict):
    engine = get_skill_engine()
    result = await engine.execute("llm.chat", payload)
    return ResponseModel(ok=result.get("ok", False), data=result.get("data"))


@router.get("/models")
def list_models(preferred: Optional[str] = None):
    router = LLMRouter()
    try:
        model = router.select(preferred_model=preferred)
        return ResponseModel(ok=True, data={"selected": model})
    except Exception as exc:
        return ResponseModel(ok=False, error=str(exc))


@router.get("/health")
def health():
    engine = get_skill_engine()
    result = __import__("asyncio").run(engine.execute("llm.health", {}))
    return ResponseModel(ok=result.get("ok", False), data=result.get("data"), error=result.get("error"))
