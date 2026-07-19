"""Desktop automation + screen understanding (Phase B; reference §7).

Mirrors the roadmap's "Desktop Automation" + "Screen Perception" tools. Because
moving the real mouse / sending real keystrokes is *high danger* (it acts on
whatever window is focused), every action goes through human confirmation and is
a no-op when pyautogui is not installed or confirmation is declined.

Screen *perception* (read-only, moderate) is now twofold:
* OCR via Tesseract (pytesseract) when available, and
* an optional vision-LLM description when a vision-capable provider is wired.
This lets Jarvis actually *read* the screen and act on UI, the core of
"do anything on this computer".
"""
from __future__ import annotations

import io
import os
import subprocess
import tempfile
from typing import Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult


def _have_pyautogui() -> bool:
    try:
        import pyautogui  # noqa: F401

        return True
    except Exception:
        return False


def _tesseract_cmd() -> str:
    """Best-effort path to the Tesseract binary.

    pytesseract is only a wrapper; it needs the real `tesseract` executable.
    We try the standard Windows install location first, then fall back to
    whatever is on PATH. Returns "" if neither is found.
    """
    candidate = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(candidate):
        return candidate
    return "tesseract"  # rely on PATH


def _ocr_text(img) -> str:
    """Run Tesseract OCR on a PIL image; '' if OCR is unavailable."""
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()
        return pytesseract.image_to_string(img).strip()
    except Exception:
        return ""


def _capture(region: str = ""):
    """Return a PIL Image of the screen (or cropped region). Raises if deps missing."""
    import pyautogui
    from PIL import Image

    bbox = None
    if region:
        bbox = tuple(int(v) for v in region.split(","))
    return pyautogui.screenshot(region=bbox)


class DesktopClickTool(Tool):
    name = "desktop_click"
    description = "Move the mouse and click at screen coordinates (HIGH danger - requires confirmation)."
    danger = "high"
    schema = {"x": "int", "y": "int", "button": "left|right (default left)"}

    def run(self, ctx: ToolContext, x: int = 0, y: int = 0, button: str = "left", **_: Any) -> ToolResult:
        if not ctx.confirm(f"Jarvis wants to click at ({x},{y}) with the {button} button. Allow?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        if not _have_pyautogui():
            return ToolResult(ok=False, output="", tool=self.name, error="pyautogui not installed (pip install pyautogui).")
        import pyautogui

        pyautogui.click(x, y, button=button)
        return ToolResult(ok=True, output=f"Clicked at ({x},{y}).", tool=self.name)


class DesktopTypeTool(Tool):
    name = "desktop_type"
    description = "Type text into the currently focused window (HIGH danger - requires confirmation)."
    danger = "high"
    schema = {"text": "string (required)"}

    def run(self, ctx: ToolContext, text: str = "", **_: Any) -> ToolResult:
        if not text:
            return ToolResult(ok=False, output="", tool=self.name, error="text is required")
        if not ctx.confirm(f"Jarvis wants to type into the focused window: {text!r}. Allow?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        if not _have_pyautogui():
            return ToolResult(ok=False, output="", tool=self.name, error="pyautogui not installed (pip install pyautogui).")
        import pyautogui

        pyautogui.write(text)
        return ToolResult(ok=True, output=f"Typed {len(text)} chars.", tool=self.name)


class DesktopMoveTool(Tool):
    name = "desktop_move"
    description = "Move the mouse to screen coordinates without clicking (moderate - requires confirmation)."
    danger = "moderate"
    schema = {"x": "int", "y": "int"}

    def run(self, ctx: ToolContext, x: int = 0, y: int = 0, **_: Any) -> ToolResult:
        if not ctx.confirm(f"Jarvis wants to move the mouse to ({x},{y}). Allow?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        if not _have_pyautogui():
            return ToolResult(ok=False, output="", tool=self.name, error="pyautogui not installed.")
        import pyautogui

        pyautogui.moveTo(x, y)
        return ToolResult(ok=True, output=f"Moved mouse to ({x},{y}).", tool=self.name)


class DesktopHotkeyTool(Tool):
    name = "desktop_hotkey"
    description = "Press a keyboard shortcut, e.g. 'ctrl,s' or 'win,r' (HIGH danger - requires confirmation)."
    danger = "high"
    schema = {"keys": "string - comma-separated keys, e.g. 'ctrl,shift,esc'"}

    def run(self, ctx: ToolContext, keys: str = "", **_: Any) -> ToolResult:
        if not keys:
            return ToolResult(ok=False, output="", tool=self.name, error="keys is required")
        if not ctx.confirm(f"Jarvis wants to press hotkey: {keys!r}. Allow?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        if not _have_pyautogui():
            return ToolResult(ok=False, output="", tool=self.name, error="pyautogui not installed.")
        import pyautogui

        combo = [k.strip() for k in keys.split(",")]
        pyautogui.hotkey(*combo)
        return ToolResult(ok=True, output=f"Pressed {keys}.", tool=self.name)


class AppLaunchTool(Tool):
    name = "app_launch"
    description = "Open an application or file by name/path (moderate - requires confirmation)."
    danger = "moderate"
    schema = {"target": "string (required) - command, app name, or file path"}

    def run(self, ctx: ToolContext, target: str = "", **_: Any) -> ToolResult:
        if not target:
            return ToolResult(ok=False, output="", tool=self.name, error="target is required")
        if not ctx.confirm(f"Jarvis wants to launch: {target!r}. Allow?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        try:
            os.startfile(target) if hasattr(os, "startfile") else subprocess.Popen(["xdg-open", target])
            return ToolResult(ok=True, output=f"Launched {target}.", tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class ScreenshotTool(Tool):
    name = "screen_capture"
    description = "Capture the screen and run OCR to read visible text (read-only, moderate)."
    danger = "moderate"
    schema = {"region": "optional 'x,y,w,h' to crop", "save_path": "optional path to save the PNG"}

    def run(self, ctx: ToolContext, region: str = "", save_path: str = "", **_: Any) -> ToolResult:
        if not _have_pyautogui():
            return ToolResult(ok=False, output="", tool=self.name,
                              error="pyautogui/pillow not installed (pip install pyautogui pillow).")
        try:
            img = _capture(region)
            out_path = save_path or os.path.join(tempfile.gettempdir(), "jarvis_screen.png")
            img.save(out_path, format="PNG")
            try:
                text = _ocr_text(img)
                return ToolResult(ok=True,
                                  output=f"(saved {out_path})\nOCR text:\n{text or '(no text detected)'}",
                                  tool=self.name)
            except Exception:
                return ToolResult(ok=True,
                                  output=f"(saved {out_path}; OCR unavailable - install pytesseract + Tesseract)",
                                  tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class ScreenUnderstandTool(Tool):
    name = "screen_understand"
    description = "Capture the screen and DESCRIBE what is on it (OCR + optional vision-LLM). Returns text Jarvis can reason about."
    danger = "moderate"
    schema = {"region": "optional 'x,y,w,h' to crop", "vision": "bool - also ask a vision-capable provider to describe it (default false)"}

    def run(self, ctx: ToolContext, region: str = "", vision: bool = False, **_: Any) -> ToolResult:
        if not _have_pyautogui():
            return ToolResult(ok=False, output="", tool=self.name,
                              error="pyautogui/pillow not installed (pip install pyautogui pillow).")
        try:
            img = _capture(region)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_b64 = buf.getvalue()

            parts = []
            # 1) OCR (always attempted)
            try:
                ocr = _ocr_text(img)
                parts.append("OCR text:\n" + (ocr or "(no text detected)"))
            except Exception:
                parts.append("(OCR unavailable - install pytesseract + Tesseract)")

            # 2) Optional vision-LLM description
            if vision:
                prov = getattr(ctx, "provider", None)
                if prov is not None and hasattr(prov, "understand_image"):
                    try:
                        desc = prov.understand_image(png_b64, "Describe this screen and list interactive elements.")
                        parts.append("Vision description:\n" + desc)
                    except Exception as e:
                        parts.append(f"(vision unavailable: {e})")
                else:
                    parts.append("(no vision-capable provider configured)")

            return ToolResult(ok=True, output="\n\n".join(parts), tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))
