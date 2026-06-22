"""Shared type definitions."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TimestampedModel(BaseModel):
    """Base model with created/updated timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ResponseModel(BaseModel):
    """Standard API response envelope."""

    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None
