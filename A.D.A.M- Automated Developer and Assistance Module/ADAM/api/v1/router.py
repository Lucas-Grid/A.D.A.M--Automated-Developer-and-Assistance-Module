"""Main API router for v1."""
from fastapi import APIRouter

from ADAM.api.v1 import registry, skills, system, workspaces

api_router = APIRouter()

api_router.include_router(registry.router, prefix="/registry", tags=["registry"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
