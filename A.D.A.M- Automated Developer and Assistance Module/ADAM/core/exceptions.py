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
