"""Centralized database initialization for ADAM OS."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ADAM.core.database import Base, get_engine
from ADAM.core.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def initialize_database() -> list[str]:
    """Create all SQLAlchemy-managed tables and ensure legacy table coverage.

    Returns:
        List of table names that were created/verified.
    """
    created: list[str] = []

    # SQLAlchemy-managed tables (forward compatibility; currently no ORM models)
    Base.metadata.create_all(bind=get_engine())
    created.extend([t.name for t in Base.metadata.tables.values()])

    # Legacy raw-SQLite tables (existing _ensure_table() implementations)
    _ensure_legacy_tables()

    logger.info("Database initialized at %s", get_settings().db_path)
    return created


def _ensure_legacy_tables() -> None:
    """Ensure all existing raw-SQLite tables exist."""
    # Import here to avoid circular imports at module load time
    from ADAM.core.registry import ProjectRegistry
    from ADAM.agents.registry import AgentRegistry
    from ADAM.automations.registry import AutomationRegistry
    from ADAM.automations.workflow import WorkflowStore
    from ADAM.automations.history import JobHistory
    from ADAM.knowledge.graph import EntityStore
    from ADAM.memory.store import MemoryStore
    from ADAM.workspace.manager import WorkspaceManager
    from ADAM.connections.model_registry import ModelRegistry

    ProjectRegistry()._ensure_table()
    AgentRegistry()._ensure_table()
    AutomationRegistry()._ensure_table()
    WorkflowStore()._ensure_table()
    JobHistory()._ensure_table()
    EntityStore()._ensure_table()
    MemoryStore()._ensure_tables()
    WorkspaceManager()._ensure_table()
    ModelRegistry()._ensure_table()
