"""Automation skills for ADAM OS."""
from __future__ import annotations

import asyncio
from typing import Any

from ADAM.automations.executor import get_execution_engine
from ADAM.automations.registry import get_automation_registry
from ADAM.automations.workflow import Workflow, get_workflow_store
from ADAM.skills.base import BaseSkill


class AutomationCreateSkill(BaseSkill):
    name = "automation.create"
    description = "Create a new automation definition"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        registry = get_automation_registry()
        workflow_id = params["workflow_id"]
        steps = params["steps"]
        metadata = params.get("metadata", {})

        workflow_store = get_workflow_store()
        workflow = workflow_store.create(Workflow(workflow_id=workflow_id, steps=steps, metadata=metadata))

        automation = {
            "automation_id": params["automation_id"],
            "name": params["name"],
            "description": params.get("description"),
            "enabled": params.get("enabled", True),
            "trigger_type": params["trigger_type"],
            "trigger_config": params.get("trigger_config", {}),
            "workflow_id": workflow_id,
        }
        created = registry.create(automation)
        return {"automation": created, "workflow": workflow.to_dict()}


class AutomationRunSkill(BaseSkill):
    name = "automation.run"
    description = "Run a registered automation workflow"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        automation_id = params["automation_id"]
        registry = get_automation_registry()
        automation = registry.get(automation_id)
        if not automation:
            raise ValueError(f"Automation '{automation_id}' not found")

        workflow_id = automation["workflow_id"]
        workflow_store = get_workflow_store()
        workflow = workflow_store.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found for automation '{automation_id}'")

        engine = get_execution_engine()
        result = await engine.execute_workflow(workflow_id, workflow.steps)
        return result


class AutomationListSkill(BaseSkill):
    name = "automation.list"
    description = "List registered automations"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        registry = get_automation_registry()
        trigger_type = params.get("trigger_type")
        items = registry.list_automations(trigger_type=trigger_type)
        return {"automations": items}


class AutomationEnableSkill(BaseSkill):
    name = "automation.enable"
    description = "Enable an automation"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        automation_id = params["automation_id"]
        registry = get_automation_registry()
        updated = registry.update(automation_id, {"enabled": True})
        return {"automation": updated}


class AutomationDisableSkill(BaseSkill):
    name = "automation.disable"
    description = "Disable an automation"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        automation_id = params["automation_id"]
        registry = get_automation_registry()
        updated = registry.update(automation_id, {"enabled": False})
        return {"automation": updated}
