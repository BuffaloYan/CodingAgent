"""
agent/browser_tool.py
Headless browser tools powered by Playwright.
Provides screenshot, page content extraction, and HTTP smoke-testing.
"""

from __future__ import annotations

import base64
from pathlib import Path

from langchain_core.tools import tool


def make_browser_tools(project_root: Path) -> list:
    """Return Playwright-based tools bound to *project_root*."""

    def _get_browser():
        """Lazy-load a Playwright browser (one per process)."""
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        return browser

    @tool
    def screenshot_html(file_path: str, width: int = 1280, height: int = 720) -> str:
        """
        Open an HTML file from the project in a headless browser and take a screenshot.
        The screenshot is saved as a PNG next to the HTML file.
        file_path is relative to the project root.
        Returns the path to the saved screenshot.
        """
        resolved = (project_root / file_path).resolve()
        if not str(resolved).startswith(str(project_root.resolve())):
            return "ERROR: Access denied — path is outside the project root."
        if not resolved.exists():
            return f"ERROR: File not found: {file_path}"

        screenshot_path = resolved.with_suffix(".screenshot.png")

        try:
            browser = _get_browser()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"file://{resolved}", wait_until="networkidle", timeout=15000)
            page.screenshot(path=str(screenshot_path), full_page=True)
            page.close()

            rel = screenshot_path.relative_to(project_root)
            return f"OK: Screenshot saved to {rel} ({screenshot_path.stat().st_size} bytes)"
        except Exception as e:
            return f"ERROR taking screenshot: {e}"

    @tool
    def browse_url(url: str, width: int = 1280, height: int = 720) -> str:
        """
        Open a URL in a headless browser, take a screenshot, and extract text content.
        The screenshot is saved as screenshots/<sanitized_url>.png in the project.
        Use for smoke-testing local servers (e.g. http://localhost:8000/api/health).
        Returns the page title, status, and path to the screenshot.
        """
        screenshots_dir = project_root / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)

        # Sanitize URL for filename
        safe_name = url.replace("://", "_").replace("/", "_").replace("?", "_")[:80]
        screenshot_path = screenshots_dir / f"{safe_name}.png"

        try:
            browser = _get_browser()
            page = browser.new_page(viewport={"width": width, "height": height})
            response = page.goto(url, wait_until="networkidle", timeout=15000)

            title = page.title() or "(no title)"
            status = response.status if response else "unknown"

            # Extract visible text (truncated)
            text = page.inner_text("body")
            if len(text) > 2000:
                text = text[:2000] + "\n… (truncated)"

            page.screenshot(path=str(screenshot_path), full_page=True)
            page.close()

            rel = screenshot_path.relative_to(project_root)
            return (
                f"Status: {status}\n"
                f"Title: {title}\n"
                f"Screenshot: {rel}\n"
                f"---\n{text}"
            )
        except Exception as e:
            return f"ERROR browsing URL: {e}"

    @tool
    def get_page_content(url: str) -> str:
        """
        Fetch a URL with a real browser and return the rendered HTML source.
        Useful for pages that require JavaScript rendering.
        """
        try:
            browser = _get_browser()
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=15000)
            content = page.content()
            page.close()

            if len(content) > 5000:
                content = content[:5000] + "\n<!-- truncated -->"
            return content
        except Exception as e:
            return f"ERROR fetching page: {e}"

    return [screenshot_html, browse_url, get_page_content]
