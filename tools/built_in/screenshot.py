import uuid
import pathlib
from typing import Any
from pydantic import BaseModel, Field

from tools.base import Tool, ToolResult, ToolInvocation, ToolKind

class ScreenshotParams(BaseModel):
    url: str = Field(..., description="The URL to navigate to and capture.")
    full_page: bool = Field(True, description="Whether to capture the entire scrolling page or just the viewport.")


class ScreenshotTool(Tool):
    name = "browser_screenshot"
    description = "Launch an invisible browser, navigate to a URL (e.g. http://localhost:5173), and take a screenshot. Useful for visually verifying UI changes."
    kind = ToolKind.READ
    schema = ScreenshotParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ScreenshotParams(**invocation.params)
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return ToolResult.error_result("Playwright is not installed. Please run `pip install playwright`.")
            
        screenshot_dir = pathlib.Path.cwd() / ".agent_scratch" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        filename = screenshot_dir / f"screenshot_{uuid.uuid4().hex[:8]}.png"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Create a context with a standard desktop viewport
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    device_scale_factor=2
                )
                page = await context.new_page()
                
                # Navigate to the URL
                await page.goto(params.url, wait_until="networkidle", timeout=15000)
                
                # Wait a brief moment for any final React/Vue animations to settle
                await page.wait_for_timeout(1000)
                
                await page.screenshot(path=str(filename), full_page=params.full_page)
                
                await browser.close()
                
            return ToolResult.success_result(f"Screenshot successfully captured and saved to: {filename}\nThe AI can now see this image to verify layout and styling.")
            
        except Exception as e:
            return ToolResult.error_result(f"Failed to capture screenshot of {params.url}: {e}")
