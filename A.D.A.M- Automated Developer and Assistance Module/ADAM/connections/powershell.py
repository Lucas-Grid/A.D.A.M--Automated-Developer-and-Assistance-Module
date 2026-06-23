"""PowerShell connector — safe subprocess execution."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from ADAM.core.config import get_settings
from ADAM.core.exceptions import PowerShellError

logger = logging.getLogger(__name__)

# PowerShell injection patterns to reject
_INJECTION_PATTERNS = [
    re.compile(r'\bRead-Host\b', re.IGNORECASE),
    re.compile(r'\bGet-Credential\b', re.IGNORECASE),
    re.compile(r'\bInvoke-Expression\b', re.IGNORECASE),
    re.compile(r'\bIEX\b', re.IGNORECASE),
    re.compile(r'\bStart-Process\b', re.IGNORECASE),
    re.compile(r'\bNew-Object\b.*System\.Net\.WebClient', re.IGNORECASE),
    re.compile(r'\bDownloadFile\b', re.IGNORECASE),
    re.compile(r'\$\(.*\)', re.DOTALL),  # subexpression injection
    re.compile(r'`[`$@\'\"]'),  # backtick escapes in suspicious context
    re.compile(r'^\s*;\s*'),  # leading semicolon
    re.compile(r';\s*$'),  # trailing semicolon
    re.compile(r'\bRemove-Item\s+.*-Recurse\b', re.IGNORECASE),  # destructive filesystem ops
    re.compile(r'\bSet-Content\b', re.IGNORECASE),  # file write
    re.compile(r'\bOut-File\b', re.IGNORECASE),  # file write
]

# Allowed PowerShell command patterns (whitelist of safe cmdlets for common ops)
_SAFE_CMD_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.\s\(\)\{\}\[\]\:\"\'\|\,\?\/\\=><!&@#\$\*\s\+\%\^~`]+$')


def _escape_for_powershell_command(value: str) -> str:
    """Escape a string for safe embedding in a PowerShell -Command argument.

    This is NOT POSIX shlex.quote; it handles PowerShell-specific escaping:
    - Single-quotes inside single-quoted strings become '' (PowerShell escape)
    - Backticks are escaped only in non-whitelist contexts (handled by rejection above)
    """
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")

    # Replace single-quote with PowerShell-escaped single quote
    escaped = value.replace("'", "''")
    return escaped


def validate_powershell_script(script: str) -> None:
    """Validate a PowerShell script for injection patterns.

    Raises PowerShellError if the script contains suspicious patterns.
    """
    if not isinstance(script, str):
        raise TypeError(f"Expected str, got {type(script).__name__}")

    if not script.strip():
        raise PowerShellError("Empty PowerShell script")

    # Reject known dangerous patterns
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(script):
            raise PowerShellError(
                f"PowerShell script rejected: potential injection pattern detected: {pattern.pattern}"
            )

    # Reject control characters (except newline/tab for readability)
    for ch in script:
        code = ord(ch)
        if code < 32 and code not in (9, 10):
            raise PowerShellError(f"PowerShell script contains control character: {code}")


class PowerShellConnector:
    """Execute PowerShell commands in a controlled subprocess."""

    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or get_settings().powershell_executable

    def execute(self, script: str, *, timeout: int = 30) -> dict[str, Any]:
        """Run a PowerShell script and return parsed result."""
        validate_powershell_script(script)

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
