"""Agent API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from ADAM.agents.lifecycle import AgentLifecycle
from ADAM.agents.registry import get_agent_registry
from ADAM.core.exceptions import AgentError
from ADAM.core.types import ResponseModel
from ADAM.skills.engine import get_skill_engine

router = APIRouter()


@router.post("/", response_model=ResponseModel)
def create_agent(payload: dict):
    engine = get_skill_engine()
    result = __import__("asyncio").run(engine.execute("agent.create", payload))
    return ResponseModel(ok=result["ok"], data=result)


@router.get("/", response_model=ResponseModel)
def list_agents(enabled: Optional[bool] = None):
    engine = get_skill_engine()
    params = {}
    if enabled is not None:
        params["enabled"] = enabled
    result = __import__("asyncio").run(engine.execute("agent.list", params))
    return ResponseModel(ok=result["ok"], data=result)


@router.post("/{agent_id}/enable", response_model=ResponseModel)
def enable_agent(agent_id: str):
    engine = get_skill_engine()
    result = __import__("asyncio").run(engine.execute("agent.enable", {"id": agent_id}))
    return ResponseModel(ok=result["ok"], data=result)


@router.post("/{agent_id}/disable", response_model=ResponseModel)
def disable_agent(agent_id: str):
    engine = get_skill_engine()
    result = __import__("asyncio").run(engine.execute("agent.disable", {"id": agent_id}))
    return ResponseModel(ok=result["ok"], data=result)


@router.post("/run", response_model=ResponseModel)
async def run_agent(payload: dict):
    agent_id = payload["id"]
    objective = payload["objective"]
    lifecycle = AgentLifecycle()
    result = await lifecycle.start(agent_id=agent_id, objective=objective)
    return ResponseModel(ok=True, data=result)


@router.get("/{agent_id}/history", response_model=ResponseModel)
def get_agent_history(agent_id: str, limit: int = 50):
    from ADAM.agents.memory import AgentMemory
    history = AgentMemory(agent_id).get_history(limit=limit)
    return ResponseModel(ok=True, data={"agent_id": agent_id, "history": history})
