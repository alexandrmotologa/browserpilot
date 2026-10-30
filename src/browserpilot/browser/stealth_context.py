"""Browser lifecycle management supporting Patchright and standard Playwright with stealth evasions."""

import logging
from typing import Any
from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.browser.fingerprint import get_stealth_scripts
from browserpilot.config import Settings, get_settings

logger = logging.getLogger("browserpilot.browser")


class BrowserManager:
    """Manages browser instance lifecycle, stealth configuration, and page sessions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.playwright: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.active_page: Any = None
        self.cursor: CursorMotion = CursorMotion()
        self.engine_type: str = "unknown"

    async def __aenter__(self) -> "BrowserManager":
        await self.launch()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def launch(self) -> None:
        """Initialize the browser process using Patchright if available, falling back to Playwright."""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1280,800",
        ]

        # 1. Attempt Patchright for native CDP binary evasion
        if self.settings.prefer_patchright:
            try:
                from patchright.async_api import async_playwright as async_patchright

                self.playwright = await async_patchright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=self.settings.headless,
                    args=args,
                )
                self.engine_type = "patchright"
                logger.info("Launched browser engine with patchright binary")
            except Exception as ex:
                logger.warning(
                    f"Patchright launch failed ({ex}). Falling back to standard playwright."
                )
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None

        # 2. Fallback to standard Playwright with script-level stealth
        if self.browser is None:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.settings.headless,
                args=args,
            )
            self.engine_type = "playwright"
            logger.info("Launched browser engine with standard playwright")

        # 3. Create browser context with normalized user-agent and viewport
        self.context = await self.browser.new_context(
            viewport={
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            },
            user_agent=self.settings.user_agent,
            locale="en-US",
            timezone_id="America/New_York",
            has_touch=False,
            is_mobile=False,
            device_scale_factor=1.0,
        )

        # 4. Inject stealth evasions into context
        if self.settings.use_stealth:
            for script in get_stealth_scripts():
                await self.context.add_init_script(script)

    async def new_page(self) -> Any:
        """Create and activate a new browser page."""
        if not self.context:
            raise RuntimeError("Browser context is not initialized. Call launch() first.")

        page = await self.context.new_page()
        page.set_default_timeout(self.settings.browser_timeout_ms)

        # Ensure stealth evasions are active even on headless page loads
        if self.settings.use_stealth:
            for script in get_stealth_scripts():
                try:
                    await page.add_init_script(script)
                except Exception:
                    pass

            async def _on_dom_load(p: Any) -> None:
                try:
                    for script in get_stealth_scripts():
                        await p.evaluate(script)
                except Exception:
                    pass

            page.on("domcontentloaded", _on_dom_load)

        self.active_page = page
        return page

    async def get_cdp_session(self, page: Any = None) -> Any:
        """Open a Chrome DevTools Protocol session attached to the page."""
        target_page = page or self.active_page
        if not target_page:
            raise RuntimeError("No active page available for CDP session.")
        return await self.context.new_cdp_session(target_page)

    async def close(self) -> None:
        """Clean up active pages, context, and browser processes."""
        if self.context:
            try:
                await self.context.close()
            except Exception as ex:
                logger.debug(f"Error closing context: {ex}")
            self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except Exception as ex:
                logger.debug(f"Error closing browser: {ex}")
            self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as ex:
                logger.debug(f"Error stopping playwright: {ex}")
            self.playwright = None

        self.active_page = None
