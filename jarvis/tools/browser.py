"""Browser automation tool (Playwright).

Enables the assistant to drive a headless browser -- useful for "build and test
a web app", scraping, or clicking through a UI. Mirrors the browser-automation
capability cited for AutoGPT / OpenJarvis. Requires `playwright` (optional dep);
without it the tool reports a clear install hint instead of crashing.
"""
from __future__ import annotations

from typing import Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult


def _have_playwright() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except Exception:
        return False


class BrowserTool(Tool):
    name = "browser"
    description = "Open a URL in a headless browser and return the page text (or click/type via action)."
    danger = "moderate"
    schema = {
        "url": "string (required)",
        "action": "goto|click|type|text (default goto)",
        "selector": "CSS selector for click/type",
        "text": "text to type when action=type",
    }

    def run(
        self,
        ctx: ToolContext,
        url: str = "",
        action: str = "goto",
        selector: str = "",
        text: str = "",
        **_: Any,
    ) -> ToolResult:
        if not url:
            return ToolResult(ok=False, output="", tool=self.name, error="url is required")
        if not _have_playwright():
            return ToolResult(
                ok=False, output="", tool=self.name,
                error="playwright not installed. Run: pip install playwright && playwright install chromium",
            )
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=20000)
                if action == "text":
                    out = page.inner_text()
                elif action == "click":
                    if not selector:
                        browser.close()
                        return ToolResult(ok=False, output="", tool=self.name, error="selector required for click")
                    page.click(selector)
                    out = page.inner_text()
                elif action == "type":
                    if not selector:
                        browser.close()
                        return ToolResult(ok=False, output="", tool=self.name, error="selector required for type")
                    page.fill(selector, text or "")
                    out = page.inner_text()
                else:  # goto
                    out = page.inner_text()
                browser.close()
            return ToolResult(ok=True, output=(out or "(empty page)")[:4000], tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))
