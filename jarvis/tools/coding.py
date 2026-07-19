"""Agentic coding tools (Phase A): the Claude Code / Hermes half of Jarvis.

Gives the assistant first-class software-engineering capabilities:
* edit_file  -- apply a unified diff / insert / replace (not just full overwrite)
* run_shell  -- execute a command in a working dir, optionally in background
* run_tests  -- convenience wrapper that runs a project's test command
* git_status / git_diff / git_commit -- version control without leaving the loop
* init_project -- scaffold a new project from a short description

These are intentionally thin wrappers over the OS so the orchestrator's
edit -> run -> observe -> fix cycle can drive real development.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult


def _resolve(ctx: ToolContext, path: str) -> str:
    if not path:
        return ctx.workspace
    if os.path.isabs(path):
        return path
    return os.path.join(ctx.workspace, path)


def _apply_diff(text: str, diff: str, operation: str) -> str:
    """Apply a simple unified-diff / insert / replace to ``text``.

    Supported mini-operations (so an LLM can edit precisely):
      * operation == "replace": ``diff`` is ``OLD <<<<>>>> NEW`` where the
        block between markers is the old text to replace with new text.
      * operation == "insert_after": ``diff`` is inserted after the first
        occurrence of the line in ``anchor`` (handled by caller).
      * operation == "unified": a standard unified diff (@@ hunks) applied via
        patch(1) if available, else a best-effort line match.
    """
    if operation == "replace":
        if "<<<<>>>>" in diff:
            old, new = diff.split("<<<<>>>>", 1)
            if old and old not in text:
                raise ValueError("old block not found in file")
            return text.replace(old, new, 1)
        # No marker: the model supplied the entire new file contents (a common
        # habit). Treat `diff` as a full overwrite rather than failing.
        if diff:
            return diff
        raise ValueError("replace needs either 'OLD<<<<>>>>NEW' or the full new file text")


def _apply_unified(text: str, diff: str) -> str:
    """Best-effort unified-diff apply without external `patch`."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    hunks = re.findall(r"@@[^\n]*\n(.*?)(?=\n@@|\Z)", diff, re.S)
    if not hunks:
        # treat whole diff as a context diff; try to find -/+ pairs
        hunks = [diff]
    for hunk in hunks:
        hlines = hunk.splitlines()
        for hl in hlines:
            if hl.startswith("+") and not hl.startswith("+++"):
                out.append(hl[1:] + "\n")
            elif hl.startswith("-") and not hl.startswith("---"):
                # skip removed line (consume matching source line)
                i += 1
            elif hl.startswith(" "):
                out.append(hl[1:] + "\n")
                i += 1
            else:
                out.append(hl + "\n")
    return "".join(out)


class EditFileTool(Tool):
    name = "edit_file"
    description = "Edit a file precisely: apply a diff, replace a block, or insert text. Returns the result of the edit."
    danger = "moderate"
    schema = {
        "path": "string (required) - file to edit",
        "operation": "replace | unified | insert_after | append",
        "diff": "string - the change (for replace: 'OLD<<<<>>>>NEW'; for unified: a diff)",
        "anchor": "string - line to insert after (for insert_after)",
        "new_text": "string - text to insert/append (for insert_after or append)",
    }

    def run(
        self,
        ctx: ToolContext,
        path: str = "",
        operation: str = "replace",
        diff: str = "",
        anchor: str = "",
        new_text: str = "",
        **kw: Any,
    ) -> ToolResult:
        # Accept the many parameter shapes LLMs emit:
        #   path:     filename / file / filepath
        #   op:       edit / operation
        #   old/new:  the universal edit format (replace block `old` with `new`)
        #   full file overwrite: content / insert / insert_text / text
        #   append:   append
        path = path or kw.get("filename") or kw.get("file") or kw.get("filepath") or ""
        operation = kw.get("edit") or operation
        old = kw.get("old") or ""
        new = kw.get("new") or new_text or kw.get("append") or kw.get("text") or kw.get("insert_text") or ""
        content = kw.get("content") or kw.get("insert") or ""
        if not path:
            return ToolResult(ok=False, output="", tool=self.name, error="path is required")
        target = _resolve(ctx, path)
        target_exists = os.path.isfile(target)
        if not target_exists:
            # Creating a NEW file is allowed (the model's primary write path).
            # Require explicit content so we never write an empty file by accident.
            has_content = bool(content or diff or new or old or new_text or kw.get("insert") or kw.get("insert_text") or kw.get("text"))
            if not has_content and operation not in ("append",):
                return ToolResult(
                    ok=False, output="", tool=self.name,
                    error="path does not exist and no content was supplied to create it. "
                          "Send the edit_file JSON with the path only, then put the ENTIRE "
                          "new file in a fenced code block (``` ... ```) right after it.",
                )
            if not ctx.confirm(f"Create new file {target}?"):
                return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
            # Ensure the parent directory exists.
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write("")  # create empty; the edit below fills it
        else:
            if not ctx.confirm(f"Edit {target}?"):
                return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            if old or new:
                # Universal old -> new block replace.
                if old and old not in text:
                    return ToolResult(
                        ok=False, output="", tool=self.name,
                        error="old block not found in file. To overwrite the whole file, "
                              "respond with the edit_file JSON (path only) followed by the "
                              "ENTIRE file in a fenced code block (no 'old'/'new').",
                    )
                new = text.replace(old, new, 1) if old else (new or text)
            elif operation in ("insert_after",):
                if not anchor:
                    return ToolResult(ok=False, output="", tool=self.name, error="insert_after needs anchor")
                if anchor not in text:
                    return ToolResult(ok=False, output="", tool=self.name, error="anchor not found")
                new = text.replace(anchor, anchor + "\n" + new, 1)
            elif operation == "append":
                new = text + ("\n" if not text.endswith("\n") else "") + new
            elif content:
                # Model supplied the entire new file contents directly.
                new = content
            else:
                new = _apply_diff(text, diff, operation)
            if not new:
                return ToolResult(
                    ok=False, output="", tool=self.name,
                    error="no content to write. Send the edit_file JSON with the path only, "
                          "then put the ENTIRE file in a fenced code block (``` ... ```) right after it.",
                )
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(new)
            return ToolResult(ok=True, output=f"Edited {target} ({len(new)} chars).", tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class RunShellTool(Tool):
    name = "run_shell"
    description = "Run a shell command in the workspace (or a given cwd). Captures stdout/stderr and exit code."
    danger = "moderate"
    schema = {
        "command": "string (required) - command to run",
        "cwd": "string - working directory (default workspace)",
        "timeout": "seconds (default 60)",
        "background": "bool - run without waiting (returns a pid)",
    }

    def run(
        self,
        ctx: ToolContext,
        command: str = "",
        cmd: str = "",
        cwd: str = "",
        timeout: int = 60,
        background: bool = False,
        **_: Any,
    ) -> ToolResult:
        command = command or cmd
        if not command:
            return ToolResult(ok=False, output="", tool=self.name, error="command is required")
        workdir = _resolve(ctx, cwd) if cwd else ctx.workspace
        try:
            if background:
                proc = subprocess.Popen(
                    command, shell=True, cwd=workdir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                )
                return ToolResult(ok=True, output=f"started pid={proc.pid}", tool=self.name)
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=workdir,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return ToolResult(
                ok=proc.returncode == 0,
                output=out or "(no output)",
                tool=self.name,
                error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output="", tool=self.name, error=f"timed out after {timeout}s")
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class RunTestsTool(Tool):
    name = "run_tests"
    description = "Run a project's test suite. Auto-detects pytest/unittest, or run an explicit command."
    danger = "moderate"
    schema = {"command": "string (optional) - override test command", "cwd": "string - default workspace"}

    def run(self, ctx: ToolContext, command: str = "", cwd: str = "", **_: Any) -> ToolResult:
        import os as _os

        workdir = _resolve(ctx, cwd) if cwd else ctx.workspace
        cmd = command or ""
        if not cmd:
            has_tests = (
                _os.path.isfile(_os.path.join(workdir, "pytest.ini"))
                or _os.path.isdir(_os.path.join(workdir, "tests"))
                or _has_test_files(workdir)
            )
            if has_tests:
                # prefer pytest if importable, else fall back to unittest
                try:
                    import importlib.util as _ilu

                    have_pytest = _ilu.find_spec("pytest") is not None
                except Exception:
                    have_pytest = False
                if have_pytest:
                    cmd = "python -m pytest -q"
                else:
                    # Run unittest via a generated runner script: `python -m
                    # unittest discover` crashes or finds 0 tests on some
                    # layouts (__file__ is None; non-package dirs are skipped;
                    # modules loaded via importlib aren't always introspected),
                    # so collect test_* callables explicitly.
                    runner = _os.path.join(workdir, "_jarvis_run_tests.py")
                    with open(runner, "w", encoding="utf-8") as _rf:
                        _rf.write(
                            "import sys, glob, os, importlib.util, unittest\n"
                            "suite = unittest.TestSuite()\n"
                            "for _p in glob.glob('test_*.py'):\n"
                            "    _name = os.path.splitext(os.path.basename(_p))[0]\n"
                            "    _spec = importlib.util.spec_from_file_location(_name, _p)\n"
                            "    _mod = importlib.util.module_from_spec(_spec)\n"
                            "    _spec.loader.exec_module(_mod)\n"
                            "    sys.modules[_name] = _mod\n"
                            "    for _attr in dir(_mod):\n"
                            "        if _attr.startswith('test') and callable(getattr(_mod, _attr)):\n"
                            "            suite.addTest(unittest.FunctionTestCase(getattr(_mod, _attr)))\n"
                            "res = unittest.TextTestRunner(verbosity=1).run(suite)\n"
                            "sys.exit(0 if res.wasSuccessful() else 1)\n"
                        )
                    cmd = f'python "{runner}"'
            else:
                cmd = "python -m unittest discover"
        # Make the project itself importable (handles src/ and flat layouts).
        env_path = workdir + _os.pathsep + _os.path.join(workdir, "src")
        import subprocess as _sp

        env = dict(_os.environ)
        env["PYTHONPATH"] = env_path + _os.pathsep + env.get("PYTHONPATH", "")
        try:
            proc = _sp.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd=workdir, env=env)
            out = (proc.stdout or "") + (proc.stderr or "")
            return ToolResult(
                ok=proc.returncode == 0,
                output=out or "(no output)",
                tool=self.name,
                error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            )
        except _sp.TimeoutExpired:
            return ToolResult(ok=False, output="", tool=self.name, error="tests timed out after 120s")
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))
        finally:
            # remove the generated runner so it doesn't pollute the repo
            try:
                _os.remove(_os.path.join(workdir, "_jarvis_run_tests.py"))
            except OSError:
                pass


def _has_test_files(workdir: str) -> bool:
    for root, _, files in os.walk(workdir):
        if "node_modules" in root or ".git" in root:
            continue
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                return True
    return False


class GitStatusTool(Tool):
    name = "git_status"
    description = "Show git status (short) for the workspace repo."
    danger = "safe"
    schema = {"cwd": "string - default workspace"}

    def run(self, ctx: ToolContext, cwd: str = "", **_: Any) -> ToolResult:
        workdir = _resolve(ctx, cwd) if cwd else ctx.workspace
        return RunShellTool().run(ctx, command="git status --short", cwd=workdir, timeout=20)


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Show the unstaged git diff for the workspace repo."
    danger = "safe"
    schema = {"cwd": "string - default workspace"}

    def run(self, ctx: ToolContext, cwd: str = "", **_: Any) -> ToolResult:
        workdir = _resolve(ctx, cwd) if cwd else ctx.workspace
        return RunShellTool().run(ctx, command="git diff", cwd=workdir, timeout=20)


class GitCommitTool(Tool):
    name = "git_commit"
    description = "Stage all changes and create a git commit with the given message."
    danger = "high"
    schema = {"message": "string (required) - commit message", "cwd": "string - default workspace"}

    def run(self, ctx: ToolContext, message: str = "", cwd: str = "", **_: Any) -> ToolResult:
        if not message:
            return ToolResult(ok=False, output="", tool=self.name, error="message is required")
        workdir = _resolve(ctx, cwd) if cwd else ctx.workspace
        if not ctx.confirm(f"Commit changes in {workdir} with message: {message!r}?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        shell = RunShellTool()
        r1 = shell.run(ctx, command="git add -A", cwd=workdir, timeout=20)
        if not r1.ok:
            return r1
        return shell.run(ctx, command=f'git commit -m "{message}"', cwd=workdir, timeout=30)


class InitProjectTool(Tool):
    name = "init_project"
    description = "Scaffold a new project directory with a basic structure for the given language."
    danger = "moderate"
    schema = {
        "name": "string (required) - project name (becomes a subdir)",
        "language": "python | node | generic (default python)",
        "description": "string - short description (stored in a README)",
    }

    TEMPLATES = {
        "python": {
            "README.md": "# {name}\n\n{desc}\n",
            "requirements.txt": "",
            "src/{name}/__init__.py": "",
            "main.py": 'def main():\n    print("Hello from {name}")\n\n\nif __name__ == "__main__":\n    main()\n',
            "tests/test_smoke.py": "def test_smoke():\n    assert True\n",
        },
        "node": {
            "README.md": "# {name}\n\n{desc}\n",
            "package.json": '{\n  "name": "{name}",\n  "version": "0.1.0",\n  "scripts": {"start": "node index.js", "test": "echo no tests"}\n}\n',
            "index.js": 'console.log("{name} started");\n',
        },
        "generic": {
            "README.md": "# {name}\n\n{desc}\n",
        },
    }

    def run(self, ctx: ToolContext, name: str = "", language: str = "python", description: str = "", **_: Any) -> ToolResult:
        if not name:
            return ToolResult(ok=False, output="", tool=self.name, error="name is required")
        lang = (language or "python").lower()
        if lang not in self.TEMPLATES:
            return ToolResult(ok=False, output="", tool=self.name, error=f"unsupported language: {lang}")
        if not ctx.confirm(f"Create project '{name}' ({lang}) in {ctx.workspace}?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        try:
            base = os.path.join(ctx.workspace, name)
            os.makedirs(base, exist_ok=True)
            created = []
            for rel, content in self.TEMPLATES[lang].items():
                rel = rel.format(name=name, desc=description or "")
                full = os.path.join(base, rel)
                os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
                with open(full, "w", encoding="utf-8") as fh:
                    fh.write(content.format(name=name, desc=description or ""))
                created.append(rel)
            # initialise git repo so the code loop can commit
            subprocess.run("git init -q", shell=True, cwd=base, capture_output=True, text=True)
            # Create an initial commit so later `git_commit` calls have a base.
            # Set a local identity only if git has none configured here.
            subprocess.run(
                "git config user.email jarvis@local 2>/dev/null || true; "
                "git config user.name Jarvis 2>/dev/null || true",
                shell=True, cwd=base, capture_output=True, text=True,
            )
            subprocess.run("git add -A", shell=True, cwd=base, capture_output=True, text=True)
            subprocess.run(
                'git commit -q -m "init: scaffold {name}"'.format(name=name),
                shell=True, cwd=base, capture_output=True, text=True,
            )
            return ToolResult(
                ok=True,
                output=f"Created project '{name}' ({lang}) at {base}\nFiles: " + ", ".join(created),
                tool=self.name,
            )
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))
