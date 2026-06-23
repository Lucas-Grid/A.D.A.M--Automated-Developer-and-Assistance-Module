"""Main API router for v1."""
from fastapi import APIRouter

from ADAM.api.v1 import registry, skills, system, workspaces, models, automations, knowledge, aiops, agents, llm, ecc

api_router = APIRouter()

api_router.include_router(registry.router, prefix="/registry", tags=["registry"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(automations.router, prefix="/automations", tags=["automations"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(aiops.router, prefix="/vector", tags=["vector"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(ecc.router, prefix="/ecc", tags=["ecc"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
