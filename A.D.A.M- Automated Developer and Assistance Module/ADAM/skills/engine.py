"""Skill engine: discovery, loading, execution."""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, Type

from ADAM.core.exceptions import SkillError
from ADAM.skills.base import BaseSkill
from ADAM.skills.registry import SkillManifest, SkillRegistry

logger = logging.getLogger(__name__)


class SkillEngine:
    """Loads and executes registered skills."""

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or SkillRegistry()
        self._loaded: dict[str, BaseSkill] = {}

    def discover(self) -> None:
        """Discover built-in and external skill entrypoints."""
        # Built-in discovery (stub for future filesystem scan)
        from ADAM.skills.builtins.system import SystemSkill  # noqa: F401
        from ADAM.skills.workspace.skills import (  # noqa: F401
            WorkspaceAnalyzeSkill,
            WorkspaceScanSkill,
            WorkspaceSummarySkill,
        )
        from ADAM.skills.model.skills import (  # noqa: F401
            ModelDiscoverSkill,
            ModelHealthSkill,
            ModelListSkill,
            ModelSelectSkill,
        )
        from ADAM.skills.automation.skills import (  # noqa: F401
            AutomationCreateSkill,
            AutomationDisableSkill,
            AutomationEnableSkill,
            AutomationListSkill,
            AutomationRunSkill,
        )
        from ADAM.skills.knowledge.skills import (  # noqa: F401
            KnowledgeAddEntitySkill,
            KnowledgeAddRelationshipSkill,
            KnowledgeContextSkill,
            KnowledgeSearchSkill,
        )
        from ADAM.skills.aiops.skills import (  # noqa: F401
            ContextBuildSkill,
            MemoryReindexSkill,
            VectorIndexSkill,
            VectorSearchSkill,
        )
        from ADAM.skills.agents.skills import (  # noqa: F401
            AgentCreateSkill,
            AgentDisableSkill,
            AgentEnableSkill,
            AgentListSkill,
            AgentRunSkill,
        )
        from ADAM.skills.agents.builtins import seed_builtin_agents
        from ADAM.skills.llm.skills import (  # noqa: F401
            LLMChatSkill,
            LLMHealthSkill,
            LLMRouteSkill,
            LLMStreamSkill,
        )
        from ADAM.skills.ecc.skills import (  # noqa: F401
            ECCPlanSkill,
            ECCReasonSkill,
            ECCReflectSkill,
            ECCValidateSkill,
        )

        seed_builtin_agents()

        builtins = [
            ("system.status", SystemSkill, ["builtin", "system"]),
            ("workspace.scan", WorkspaceScanSkill, ["workspace", "builtin"]),
            ("workspace.analyze", WorkspaceAnalyzeSkill, ["workspace", "builtin"]),
            ("workspace.summary", WorkspaceSummarySkill, ["workspace", "builtin"]),
            ("model.discover", ModelDiscoverSkill, ["model", "builtin"]),
            ("model.list", ModelListSkill, ["model", "builtin"]),
            ("model.health", ModelHealthSkill, ["model", "builtin"]),
            ("model.select", ModelSelectSkill, ["model", "builtin"]),
            ("automation.create", AutomationCreateSkill, ["automation", "builtin"]),
            ("automation.run", AutomationRunSkill, ["automation", "builtin"]),
            ("automation.list", AutomationListSkill, ["automation", "builtin"]),
            ("automation.enable", AutomationEnableSkill, ["automation", "builtin"]),
            ("automation.disable", AutomationDisableSkill, ["automation", "builtin"]),
            ("knowledge.add_entity", KnowledgeAddEntitySkill, ["knowledge", "builtin"]),
            ("knowledge.add_relationship", KnowledgeAddRelationshipSkill, ["knowledge", "builtin"]),
            ("knowledge.search", KnowledgeSearchSkill, ["knowledge", "builtin"]),
            ("knowledge.context", KnowledgeContextSkill, ["knowledge", "builtin"]),
            ("vector.index", VectorIndexSkill, ["aiops", "builtin"]),
            ("vector.search", VectorSearchSkill, ["aiops", "builtin"]),
            ("context.build", ContextBuildSkill, ["aiops", "builtin"]),
            ("memory.reindex", MemoryReindexSkill, ["aiops", "builtin"]),
            ("agent.create", AgentCreateSkill, ["agent", "builtin"]),
            ("agent.list", AgentListSkill, ["agent", "builtin"]),
            ("agent.enable", AgentEnableSkill, ["agent", "builtin"]),
            ("agent.disable", AgentDisableSkill, ["agent", "builtin"]),
            ("agent.run", AgentRunSkill, ["agent", "builtin"]),
            ("llm.chat", LLMChatSkill, ["llm", "builtin"]),
            ("llm.stream", LLMStreamSkill, ["llm", "builtin"]),
            ("llm.health", LLMHealthSkill, ["llm", "builtin"]),
            ("llm.route", LLMRouteSkill, ["llm", "builtin"]),
            ("ecc.reason", ECCReasonSkill, ["ecc", "builtin"]),
            ("ecc.plan", ECCPlanSkill, ["ecc", "builtin"]),
            ("ecc.validate", ECCValidateSkill, ["ecc", "builtin"]),
            ("ecc.reflect", ECCReflectSkill, ["ecc", "builtin"]),
        ]
        for name, cls, tags in builtins:
            try:
                self.registry.register(
                    SkillManifest(
                        name=cls.name,
                        description=cls.description,
                        entrypoint=f"{cls.__module__}.{cls.__name__}",
                        tags=tags,
                    )
                )
            except SkillError:
                pass

    def load(self, name: str) -> BaseSkill:
        """Load (instantiate) a skill by name."""
        if name in self._loaded:
            return self._loaded[name]

        manifest = self.registry.get(name)
        module_path, class_name = manifest.entrypoint.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls: Type[BaseSkill] = getattr(module, class_name)
        instance = cls()
        self._loaded[name] = instance
        return instance

    async def execute(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a skill by name with provided parameters."""
        try:
            skill = self.load(name)
            skill.validate_params(params)
            result = await skill.execute(params)
            return {"skill": name, "ok": True, "result": result}
        except Exception as exc:
            logger.exception("Skill execution failed: %s", name)
            return {"skill": name, "ok": False, "error": str(exc)}

    def list_skills(self) -> list[dict]:
        return [
            {
                "name": m.name,
                "description": m.description,
                "version": m.version,
                "enabled": m.enabled,
                "tags": list(m.tags),
            }
            for m in self.registry.list()
        ]


# Singleton
_engine: SkillEngine | None = None


def get_skill_engine() -> SkillEngine:
    global _engine
    if _engine is None:
        _engine = SkillEngine()
        _engine.discover()
    return _engine
