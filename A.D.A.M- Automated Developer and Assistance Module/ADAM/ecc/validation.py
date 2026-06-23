"""ECC validation: validate plans before execution."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.core.exceptions import AgentError, SkillError
from ADAM.skills.engine import get_skill_engine

logger = logging.getLogger(__name__)


class ECCValidation:
    """Validate execution plans, skills, models, and permissions."""

    def __init__(self) -> None:
        self._engine = get_skill_engine()

    def validate_plan(self, plan: Any) -> dict[str, Any]:
        errors: list[str] = []
        for step in plan.steps:
            skill_name = step.get("skill")
            if not skill_name:
                errors.append(f"Empty skill name in step: {step}")
                continue
            try:
                self._engine.registry.get(skill_name)
            except SkillError:
                errors.append(f"Skill '{skill_name}' not available")

        if errors:
            return {"valid": False, "errors": errors}
        return {"valid": True, "errors": []}

    def validate_skills(self, skill_names: list[str]) -> dict[str, Any]:
        missing = []
        for name in skill_names:
            try:
                self._engine.registry.get(name)
            except SkillError:
                missing.append(name)
        if missing:
            return {"valid": False, "missing_skills": missing}
        return {"valid": True}
