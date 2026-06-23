"""Custom exception hierarchy for ADAM OS."""


class AdamError(Exception):
    """Base exception for ADAM OS."""


class ConfigError(AdamError):
    """Configuration error."""


class ProjectRegistryError(AdamError):
    """Project registry error."""


class MemoryError(AdamError):
    """Memory store error."""


class SkillError(AdamError):
    """Skill engine error."""


class ConnectionError(AdamError):
    """External connection error."""


class PowerShellError(ConnectionError):
    """PowerShell execution error."""


class WorkspaceError(AdamError):
    """Workspace intelligence error."""


class ModelRegistryError(AdamError):
    """Model registry error."""


class ProviderError(AdamError):
    """Provider connection/authentication error."""


class AutomationError(AdamError):
    """Automation engine error."""


class KnowledgeGraphError(AdamError):
    """Knowledge graph error."""


class AIOpsError(AdamError):
    """AI Ops and vector memory error."""


class AgentError(AdamError):
    """Agent runtime error."""
