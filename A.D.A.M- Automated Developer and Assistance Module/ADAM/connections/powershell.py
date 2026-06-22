"""PowerShell connector — safe subprocess execution."""
from __future__ import annotations

import asyncio
import json
import logging
import shlex
import subprocess
from pathlib import Path

from ADAM.core.config import get_settings
from ADAM.core.exceptions import PowerShellError

logger = logging.getLogger(__name__)


class PowerShellConnector:
    """Execute PowerShell commands in a controlled subprocess."""

    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or get_settings().powershell_executable

    def execute(self, script: str, *, timeout: int = 30) -> dict[str, Any]:
        """Run a PowerShell script and return parsed result."""
        if not script.strip():
            raise PowerShellError("Empty PowerShell script")

        # Basic safety: disallow interactive prompts
        if "Read-Host" in script or "Get-Credential" in script:
            raise PowerShellError("Interactive prompts are not allowed")

        try:
            completed = subprocess.run(
                [
                    self.executable,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                cwd=str(get_settings().workspace_dir),
            )
        except FileNotFoundError as exc:
            raise PowerShellError(f"PowerShell executable not found: {self.executable}") from exc
        except subprocess.TimeoutExpired as exc:
            raise PowerShellError(f"PowerShell execution timed out after {timeout}s") from exc

        result = {
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

        if completed.returncode != 0:
            logger.warning("PowerShell exited with code %d", completed.returncode)
            raise PowerShellError(
                f"PowerShell failed (exit {completed.returncode}):\n{result['stderr']}"
            )

        return result

    async def execute_async(self, script: str, *, timeout: int = 30) -> dict[str, Any]:
        """Async wrapper for subprocess execution."""
        return await asyncio.to_thread(self.execute, script, timeout=timeout)

    def run_command(self, command: str) -> str:
        """Run a single PowerShell command and return stdout."""
        result = self.execute(command)
        return result["stdout"]
