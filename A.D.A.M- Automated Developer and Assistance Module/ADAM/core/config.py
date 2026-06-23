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

    # Provider API keys (optional; loaded from env)
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    together_api_key: str = ""
    mistral_api_key: str = ""
    nvidia_api_key: str = ""

    # Provider endpoints (override defaults if needed)
    openai_base_url: str = "https://api.openai.com/v1"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    anthropic_base_url: str = "https://api.anthropic.com"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    together_base_url: str = "https://api.together.xyz/v1"
    mistral_base_url: str = "https://api.mistral.ai/v1"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

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
