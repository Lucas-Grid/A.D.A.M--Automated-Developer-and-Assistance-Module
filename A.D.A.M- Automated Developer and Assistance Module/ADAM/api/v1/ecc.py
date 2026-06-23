"""ECC API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from ADAM.core.types import ResponseModel
from ADAM.skills.engine import get_skill_engine

router = APIRouter()


@router.post("/reason", response_model=ResponseModel)
async def reason(payload: dict):
    engine = get_skill_engine()
    result = await engine.execute("ecc.reason", payload)
    return ResponseModel(ok=result.get("ok", False), data=result.get("data"), error=result.get("error"))


@router.post("/plan", response_model=ResponseModel)
async def plan(payload: dict):
    engine = get_skill_engine()
    result = await engine.execute("ecc.plan", payload)
    return ResponseModel(ok=result.get("ok", False), data=result.get("data"), error=result.get("error"))


@router.post("/validate", response_model=ResponseModel)
async def validate(payload: dict):
    engine = get_skill_engine()
    result = await engine.execute("ecc.validate", payload)
    return ResponseModel(ok=result.get("ok", False), data=result.get("data"), error=result.get("error"))


@router.post("/reflect", response_model=ResponseModel)
async def reflect(payload: dict):
    engine = get_skill_engine()
    result = await engine.execute("ecc.reflect", payload)
    return ResponseModel(ok=result.get("ok", False), data=result.get("data"), error=result.get("error"))
