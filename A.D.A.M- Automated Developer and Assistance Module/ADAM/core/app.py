"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ADAM.core.config import get_settings
from ADAM.core.events import startup, shutdown


def create_app() -> FastAPI:
    """Create and configure ADAM OS FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_event_handler("startup", startup)
    application.add_event_handler("shutdown", shutdown)

    from ADAM.api.v1.router import api_router

    application.include_router(api_router, prefix=settings.api_prefix)

    return application
