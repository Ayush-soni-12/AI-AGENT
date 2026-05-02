import uuid
import pathlib
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field

from tools.base import Tool, ToolResult, ToolInvocation, ToolKind


class BrowserActionParams(BaseModel):
    action: Literal["navigate", "click", "type", "screenshot", "scroll"] = Field(
        ..., description="The action to perform in the browser."
    )
    url: Optional[str] = Field(None, description="The URL to navigate to (required for 'navigate').")
    selector: Optional[str] = Field(None, description="CSS selector for the element to click or type into.")
    text: Optional[str] = Field(None, description="Text to type (required for 'type').")
    full_page: bool = Field(True, description="For 'screenshot', whether to capture the full page.")


class BrowserActionTool(Tool):
    name = "browser_action"
    description = (
        "Interact with a headless browser to navigate, click, type, and verify UI. "
        "Use this for QA testing or verifying frontend changes. "
        "Example: navigate to http://localhost:5173, then click 'button.login', then take a screenshot."
    )
    kind = ToolKind.READ
    schema = BrowserActionParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = BrowserActionParams(**invocation.params)
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return ToolResult.error_result("Playwright is not installed. Please run `pip install playwright`.")
            
        screenshot_dir = pathlib.Path.cwd() / ".agent_scratch" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        filename = screenshot_dir / f"browser_{uuid.uuid4().hex[:8]}.png"

        try:
            async with async_playwright() as p:
                # We use a persistent browser instance logic if we wanted state, 
                # but for now, we'll run a clean session per call to avoid leaks.
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    device_scale_factor=1
                )
                page = await context.new_page()
                
                # Perform the requested action
                if params.action == "navigate":
                    if not params.url:
                        return ToolResult.error_result("URL is required for 'navigate' action.")
                    await page.goto(params.url, wait_until="networkidle", timeout=20000)
                    msg = f"Navigated to {params.url}"
                
                elif params.action == "click":
                    if not params.url: return ToolResult.error_result("URL context required.")
                    if not params.selector: return ToolResult.error_result("Selector required for 'click'.")
                    await page.goto(params.url, wait_until="networkidle")
                    await page.click(params.selector)
                    msg = f"Clicked element: {params.selector}"
                
                elif params.action == "type":
                    if not params.url: return ToolResult.error_result("URL context required.")
                    if not params.selector or params.text is None: 
                        return ToolResult.error_result("Selector and text required for 'type'.")
                    await page.goto(params.url, wait_until="networkidle")
                    await page.fill(params.selector, params.text)
                    msg = f"Typed '{params.text}' into {params.selector}"

                elif params.action == "scroll":
                    if not params.url: return ToolResult.error_result("URL context required.")
                    await page.goto(params.url, wait_until="networkidle")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    msg = "Scrolled to bottom of page"

                # ALWAYS take a screenshot after an action to show the agent the result!
                await page.wait_for_timeout(1000) # Wait for renders
                await page.screenshot(path=str(filename), full_page=params.full_page)
                await browser.close()
                
            return ToolResult.success_result(
                f"{msg}. Screenshot captured to: {filename}\n"
                f"The AI can visually verify the state of the page now."
            )
            
        except Exception as e:
            return ToolResult.error_result(f"Browser action '{params.action}' failed: {e}")
