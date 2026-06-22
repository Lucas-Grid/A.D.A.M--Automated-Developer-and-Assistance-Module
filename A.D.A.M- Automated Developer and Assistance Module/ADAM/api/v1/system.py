"""System and health API endpoints."""
from fastapi import APIRouter

from ADAM.core.app import create_app
from ADAM.core.config import get_settings
from ADAM.core.types import ResponseModel

router = APIRouter()


@router.get("/health", response_model=ResponseModel)
def health_check():
    return ResponseModel(ok=True, data={"status": "healthy", "app": get_settings().app_name})


@router.get("/info", response_model=ResponseModel)
def app_info():
    s = get_settings()
    return ResponseModel(
        ok=True,
        data={
            "name": s.app_name,
            "environment": s.environment,
            "version": "0.1.0",
            "api_prefix": s.api_prefix,
        },
    )
