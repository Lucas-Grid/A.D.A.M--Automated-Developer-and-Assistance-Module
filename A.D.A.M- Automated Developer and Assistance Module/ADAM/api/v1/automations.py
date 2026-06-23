"""Automation API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from ADAM.core.types import ResponseModel
from ADAM.automations.executor import get_execution_engine
from ADAM.automations.history import get_job_history
from ADAM.automations.registry import get_automation_registry
from ADAM.skills.engine import get_skill_engine

router = APIRouter()


@router.get("/", response_model=ResponseModel)
def list_automations(trigger_type: Optional[str] = None):
    registry = get_automation_registry()
    items = registry.list_automations(trigger_type=trigger_type)
    return ResponseModel(ok=True, data={"automations": items})


@router.post("/run", response_model=ResponseModel)
async def run_automation(automation_id: str):
    engine = get_skill_engine()
    result = await engine.execute("automation.run", {"automation_id": automation_id})
    return ResponseModel(ok=result["ok"], data=result)


@router.get("/history", response_model=ResponseModel)
def get_automation_history(workflow_id: Optional[str] = None, success: Optional[bool] = None):
    history = get_job_history()
    items = history.list_jobs(workflow_id=workflow_id, success=success)
    return ResponseModel(ok=True, data={"history": items})


@router.post("/enable", response_model=ResponseModel)
async def enable_automation(automation_id: str):
    engine = get_skill_engine()
    result = await engine.execute("automation.enable", {"automation_id": automation_id})
    return ResponseModel(ok=result["ok"], data=result)


@router.post("/disable", response_model=ResponseModel)
async def disable_automation(automation_id: str):
    engine = get_skill_engine()
    result = await engine.execute("automation.disable", {"automation_id": automation_id})
    return ResponseModel(ok=result["ok"], data=result)
