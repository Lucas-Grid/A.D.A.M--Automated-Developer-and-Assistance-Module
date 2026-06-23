"""Agent definitions for ADAM OS."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Agent:
    """Agent definition."""
    id: str
    name: str
    role: str
    description: str
    model_id: Optional[str] = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
