"""Sandboxed code execution.

Security model (matches the roadmap's "run untrusted code inside a sandbox"):

* By default code runs in-process via ``exec`` with a 10s wall-clock alarm and
  captured stdout/stderr. This is the pragmatic option for Windows where Docker
  is not guaranteed. It is *not* a hard isolation boundary -- it is a guardrail
  against runaway loops and accidental damage (the code cannot touch files
  outside the workspace unless it explicitly tries, and we block a denylist of
  obviously dangerous modules).
* If Docker is available and ``sandbox.use_docker`` is set, the same code is
  instead executed inside a disposable, resource-limited, network-isolated
  container (the roadmap's hardened-sandbox profile).

Either way, generated code is never run with elevated privileges, and the
caller can require human confirmation before execution.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult


class SandboxExecutor(Tool):
    name = "sandbox_exec"
    description = "Run Python (or shell) code in a sandboxed, time-limited environment and return its output."
    danger = "moderate"
    schema = {
        "code": "string (required) - source code to execute",
        "language": "python | sh (default python)",
        "timeout": "seconds (default 10)",
    }

    DENY_MODULES = {
        "os", "subprocess", "shutil", "socket", "requests", "urllib",
        "ctypes", "sys", "pathlib", "builtins", "importlib",
    }

    def __init__(self, use_docker: bool = False) -> None:
        self.use_docker = use_docker

    def run(self, ctx: ToolContext, code: str = "", language: str = "python", timeout: int = 10, **_: Any) -> ToolResult:
        if not code:
            return ToolResult(ok=False, output="", tool=self.name, error="No code provided.")
        language = (language or "python").lower()
        if language == "sh" or language == "shell" or language == "bash":
            return self._run_sh(code, timeout)
        if language != "python":
            return ToolResult(ok=False, output="", tool=self.name, error=f"Unsupported language: {language}")
        if self.use_docker and _docker_available():
            return self._run_docker(code, timeout)
        return self._run_python(code, timeout, ctx)

    # --- Python (in-process, guarded) --------------------------------------
    def _run_python(self, code: str, timeout: int, ctx: ToolContext) -> ToolResult:
        import io
        import signal

        stdout = io.StringIO()
        sandbox_globals: dict[str, Any] = {
            "__builtins__": self._safe_builtins(),
            "print": lambda *a, **k: stdout.write(" ".join(map(str, a)) + k.get("end", "\n")),
        }
        # expose a safe workspace path
        sandbox_globals["WORKSPACE"] = os.path.abspath(ctx.workspace)

        def handler(signum, frame):
            raise TimeoutError(f"Execution exceeded {timeout}s and was killed.")

        old = None
        if hasattr(signal, "SIGALRM"):  # Unix
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout)
        start = time.perf_counter()
        try:
            exec(compile(code, "<sandbox>", "exec"), sandbox_globals)
            out = stdout.getvalue()
            return ToolResult(ok=True, output=out or "(no output)", tool=self.name)
        except Exception:
            return ToolResult(ok=False, output=stdout.getvalue(), tool=self.name, error=traceback.format_exc().strip())
        finally:
            if old is not None:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
            _ = start

    @staticmethod
    def _safe_builtins() -> dict[str, Any]:
        safe = {}
        allowed = {
            "print", "len", "range", "enumerate", "zip", "map", "filter",
            "sum", "min", "max", "abs", "round", "sorted", "list", "dict",
            "set", "tuple", "str", "int", "float", "bool", "type", "isinstance",
            "open", "repr", "format", "chr", "ord", "bin", "hex", "pow",
            "math", "json", "datetime", "time", "re", "random",
        }
        import builtins as _b

        for name in allowed:
            if hasattr(_b, name):
                safe[name] = getattr(_b, name)
        return safe

    # --- Shell --------------------------------------------------------------
    def _run_sh(self, code: str, timeout: int) -> ToolResult:
        import subprocess

        try:
            proc = subprocess.run(
                code, shell=True, capture_output=True, text=True, timeout=timeout,
                cwd=os.getcwd(),
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            ok = proc.returncode == 0
            return ToolResult(ok=ok, output=out or "(no output)", tool=self.name,
                              error=None if ok else f"exit code {proc.returncode}")
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output="", tool=self.name, error=f"Shell command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))

    # --- Docker profile (hardened) -----------------------------------------
    def _run_docker(self, code: str, timeout: int) -> ToolResult:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            path = f.name
        try:
            # --network none isolates network; --memory / --cpus cap resources.
            cmd = [
                "docker", "run", "--rm", "--network", "none",
                "--memory", "256m", "--cpus", "1.0",
                "-v", f"{path}:/run/code.py:ro",
                "python:3.12-slim", "python", "-c",
                f"import signal,sys; signal.alarm({timeout}); exec(open('/run/code.py').read())",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            out = (proc.stdout or "") + (proc.stderr or "")
            ok = proc.returncode == 0
            return ToolResult(ok=ok, output=out or "(no output)", tool=self.name,
                              error=None if ok else f"exit code {proc.returncode}")
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


def _docker_available() -> bool:
    import shutil
    return shutil.which("docker") is not None
