"""Skills API endpoints."""
from fastapi import APIRouter

from ADAM.core.types import ResponseModel
from ADAM.skills.engine import get_skill_engine

router = APIRouter()


@router.get("/", response_model=ResponseModel)
def list_skills():
    engine = get_skill_engine()
    return ResponseModel(ok=True, data=engine.list_skills())


@router.post("/{name}/execute", response_model=ResponseModel)
async def execute_skill(name: str, params: dict):
    engine = get_skill_engine()
    result = await engine.execute(name, params)
    status = 200 if result.get("ok") else 400
    return ResponseModel(ok=result["ok"], data=result)
