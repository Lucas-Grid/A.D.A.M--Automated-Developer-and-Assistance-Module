"""Application settings via Pydantic Settings."""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ADAM OS configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="ADAM_",
    )

    # Paths are resolved relative to this config file's directory (project root)
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

    # Runtime
    app_name: str = "ADAM OS"
    environment: str = "development"
    debug: bool = True

    # Data
    data_dir: Path = PROJECT_ROOT / "data"
    db_path: Path = data_dir / "adam.db"
    logs_dir: Path = PROJECT_ROOT / "logs"
    workspace_dir: Path = PROJECT_ROOT / "data" / "workspace"

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Connections
    ollama_base_url: str = "http://localhost:11434"
    powershell_executable: str = "powershell.exe"

    # Security
    allowed_workspace_roots: list[str] = []

    def model_post_init(self, __context) -> None:
        """Ensure required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)


# Singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset cached settings (for tests)."""
    global _settings
    _settings = None
