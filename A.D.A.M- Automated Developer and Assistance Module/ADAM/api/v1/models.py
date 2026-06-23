"""Model API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from ADAM.core.types import ResponseModel
from ADAM.connections.model_registry import get_model_registry
from ADAM.skills.engine import get_skill_engine

router = APIRouter()


@router.get("/", response_model=ResponseModel)
def list_models(provider: Optional[str] = None, status: Optional[str] = None):
    registry = get_model_registry()
    models = registry.list_models(provider=provider, status=status)
    return ResponseModel(ok=True, data={"models": models})


@router.post("/discover", response_model=ResponseModel)
async def discover_models(providers: Optional[list[str]] = None):
    engine = get_skill_engine()
    result = await engine.execute("model.discover", {"providers": providers})
    status = 200 if result.get("ok") else 400
    return ResponseModel(ok=result["ok"], data=result)


@router.get("/health", response_model=ResponseModel)
async def model_health(providers: Optional[list[str]] = None):
    engine = get_skill_engine()
    result = await engine.execute("model.health", {"providers": providers})
    return ResponseModel(ok=True, data=result)


@router.post("/select", response_model=ResponseModel)
async def select_model(model_id: str):
    engine = get_skill_engine()
    result = await engine.execute("model.select", {"model_id": model_id})
    status = 200 if result.get("ok") else 400
    return ResponseModel(ok=result["ok"], data=result)
