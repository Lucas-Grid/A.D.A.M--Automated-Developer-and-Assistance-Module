"""Application lifecycle events."""
import logging

from ADAM.core.config import get_settings

logger = logging.getLogger(__name__)


async def startup() -> None:
    """Run on application startup."""
    settings = get_settings()
    logger.info(
        "Starting %s [%s] on %s:%d",
        settings.app_name,
        settings.environment,
        settings.api_host,
        settings.api_port,
    )


async def shutdown() -> None:
    """Run on application shutdown."""
    logger.info("Shutting down %s", get_settings().app_name)
