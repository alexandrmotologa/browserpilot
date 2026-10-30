"""Browser lifecycle management supporting Patchright, standard Playwright, and multi-tab workflows."""

import logging
from pathlib import Path
from typing import Any
from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.browser.fingerprint import get_stealth_scripts
from browserpilot.config import Settings, get_settings

logger = logging.getLogger("browserpilot.browser")


class BrowserManager:
    """Manages browser process lifecycle, stealth evasions, multi-tab contexts, and session persistence."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.playwright: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.pages: list[Any] = []
        self.active_page: Any = None
        self.cursor: CursorMotion = CursorMotion()
        self.engine_type: str = "unknown"

    async def __aenter__(self) -> "BrowserManager":
        await self.launch()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def launch(self, storage_state_path: str | Path | None = None) -> None:
        """Initialize browser with stealth flags and optional storage state (cookies/session)."""
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

        # Resolve storage state if file exists
        state_file = None
        if storage_state_path:
            p = Path(storage_state_path)
            if p.exists():
                state_file = str(p)

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
            storage_state=state_file,
        )

        # 4. Inject stealth evasions into context
        if self.settings.use_stealth:
            for script in get_stealth_scripts():
                await self.context.add_init_script(script)

        # 5. Listen for newly spawned popup/blank tabs
        def _handle_new_page(new_p: Any) -> None:
            if new_p not in self.pages:
                self.pages.append(new_p)
                self._attach_page_evasions(new_p)
                self.active_page = new_p
                logger.info(f"New browser tab opened. Active tab count: {len(self.pages)}")

        self.context.on("page", _handle_new_page)

    def _attach_page_evasions(self, page: Any) -> None:
        """Ensure newly created or popup tabs run stealth evasions and handle close cleanup."""
        page.set_default_timeout(self.settings.browser_timeout_ms)

        if self.settings.use_stealth:
            async def _on_dom_load(p: Any) -> None:
                try:
                    for script in get_stealth_scripts():
                        await p.evaluate(script)
                except Exception:
                    pass

            page.on("domcontentloaded", _on_dom_load)

        def _on_close() -> None:
            if page in self.pages:
                self.pages.remove(page)
            if self.active_page == page:
                self.active_page = self.pages[-1] if self.pages else None
            logger.info(f"Tab closed. Remaining tabs: {len(self.pages)}")

        page.on("close", lambda: _on_close())

    async def new_page(self) -> Any:
        """Create and activate a new browser page."""
        if not self.context:
            raise RuntimeError("Browser context is not initialized. Call launch() first.")

        page = await self.context.new_page()
        if page not in self.pages:
            self.pages.append(page)
        self._attach_page_evasions(page)
        self.active_page = page
        return page

    async def get_tabs(self) -> list[dict[str, Any]]:
        """Return metadata for all open tabs."""
        tabs: list[dict[str, Any]] = []
        for idx, page in enumerate(self.pages):
            try:
                title = await page.title()
                url = page.url
            except Exception:
                title = "Untitled"
                url = "about:blank"

            tabs.append({
                "index": idx,
                "title": title or "New Tab",
                "url": url,
                "is_active": page == self.active_page,
            })
        return tabs

    async def switch_tab(self, index: int) -> Any:
        """Set active tab to the specified page index."""
        if index < 0 or index >= len(self.pages):
            raise IndexError(f"Tab index {index} out of range (0-{len(self.pages)-1})")

        page = self.pages[index]
        await page.bring_to_front()
        self.active_page = page
        logger.info(f"Switched active tab to index {index} ({page.url})")
        return page

    async def new_tab(self, url: str | None = None) -> Any:
        """Open a new tab, navigate to optional URL, and bring to front."""
        page = await self.new_page()
        if url:
            target = url if url.startswith("http") else f"https://{url}"
            await page.goto(target, wait_until="domcontentloaded")
        return page

    async def close_tab(self, index: int | None = None) -> None:
        """Close the active tab or tab at specified index."""
        target_idx = len(self.pages) - 1 if index is None else index
        if 0 <= target_idx < len(self.pages):
            page = self.pages[target_idx]
            await page.close()

    async def save_storage_state(self, path: str | Path) -> None:
        """Save cookies, session tokens, and localStorage to file."""
        if not self.context:
            raise RuntimeError("Browser context is not active.")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        await self.context.storage_state(path=str(p))
        logger.info(f"Saved session profile storage state to {p}")

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

        self.pages.clear()
        self.active_page = None
