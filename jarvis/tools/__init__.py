"""Tool package: register the built-in tool set."""
from __future__ import annotations

import os

from jarvis.tools.builtins import MemoryRecallTool, MemoryStoreTool, WebSearchTool
from jarvis.tools.browser import BrowserTool
from jarvis.tools.builder import ProjectBuilderTool
from jarvis.tools.coding import (
    EditFileTool,
    GitCommitTool,
    GitDiffTool,
    GitStatusTool,
    InitProjectTool,
    RunShellTool,
    RunTestsTool,
)
from jarvis.tools.desktop import (
    AppLaunchTool,
    DesktopClickTool,
    DesktopHotkeyTool,
    DesktopMoveTool,
    DesktopTypeTool,
    ScreenUnderstandTool,
    ScreenshotTool,
)
from jarvis.tools.files import FileListTool, FileReadTool, FileWriteTool
from jarvis.tools.knowledge import SemanticRecallTool, SemanticRememberTool, SpeakTool
from jarvis.tools.meta import MetaAgentTool
from jarvis.tools.registry import ToolRegistry, get_registry
from jarvis.tools.sandbox import SandboxExecutor


def register_default_tools(registry: ToolRegistry | None = None, use_docker: bool = False) -> ToolRegistry:
    reg = registry or get_registry()
    reg.register(SandboxExecutor(use_docker=use_docker))
    reg.register(FileListTool())
    reg.register(FileReadTool())
    reg.register(FileWriteTool())
    reg.register(WebSearchTool())
    reg.register(MemoryStoreTool())
    reg.register(MemoryRecallTool())
    reg.register(DesktopClickTool())
    reg.register(DesktopTypeTool())
    reg.register(ScreenshotTool())
    reg.register(DesktopMoveTool())
    reg.register(DesktopHotkeyTool())
    reg.register(AppLaunchTool())
    reg.register(ScreenUnderstandTool())
    reg.register(BrowserTool())
    reg.register(MetaAgentTool())
    # Semantic memory + voice (folds ADAM's vector store / TTS in; dep-light)
    reg.register(SemanticRememberTool())
    reg.register(SemanticRecallTool())
    reg.register(SpeakTool())
    # Phase A: agentic coding engine
    reg.register(EditFileTool())
    reg.register(RunShellTool())
    reg.register(RunTestsTool())
    reg.register(GitStatusTool())
    reg.register(GitDiffTool())
    reg.register(GitCommitTool())
    reg.register(InitProjectTool())
    # §10: load YAML-declared plugins from tools/plugins (best-effort)
    try:
        from jarvis.tools.plugins import load_plugins

        load_plugins(os.path.join(os.path.dirname(__file__), "plugins"), reg)
    except Exception:
        pass
    return reg


__all__ = [
    "register_default_tools",
    "SandboxExecutor",
    "FileListTool",
    "FileReadTool",
    "FileWriteTool",
    "WebSearchTool",
    "MemoryStoreTool",
    "MemoryRecallTool",
    "DesktopClickTool",
    "DesktopTypeTool",
    "ScreenshotTool",
    "BrowserTool",
    "MetaAgentTool",
]
