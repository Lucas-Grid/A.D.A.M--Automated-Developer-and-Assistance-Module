"""Connections subpackage."""
from ADAM.connections.model_registry import ModelRegistry, get_model_registry, reset_model_registry
from ADAM.connections.ollama import OllamaClient
from ADAM.connections.powershell import PowerShellConnector

__all__ = [
    "OllamaClient",
    "PowerShellConnector",
    "ModelRegistry",
    "get_model_registry",
    "reset_model_registry",
]
