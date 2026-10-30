"""Two-way viewport streaming and remote input relay for human takeover."""

import asyncio
import base64
import logging
from typing import Any, Callable

logger = logging.getLogger("browserpilot.human.relay")


class StreamRelay:
    """Relays viewport frames to remote operators and forwards remote input events to the browser."""

    def __init__(self, page_provider: Callable[[], Any | None]) -> None:
        self.page_provider = page_provider
        self.is_streaming: bool = False
        self._stream_task: asyncio.Task[None] | None = None
        self.frame_subscribers: list[Callable[[str], Any]] = []

    def subscribe(self, callback: Callable[[str], Any]) -> None:
        """Register a listener for new base64 JPEG viewport frames."""
        self.frame_subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str], Any]) -> None:
        """Remove a previously registered frame listener."""
        if callback in self.frame_subscribers:
            self.frame_subscribers.remove(callback)

    async def start_stream(self, fps: float = 6.0) -> None:
        """Begin continuous viewport frame capture loop."""
        if self.is_streaming:
            return

        self.is_streaming = True
        interval = 1.0 / max(1.0, min(15.0, fps))

        async def _loop() -> None:
            while self.is_streaming:
                page = self.page_provider()
                if page:
                    try:
                        screenshot_bytes = await page.screenshot(
                            type="jpeg", quality=55, timeout=1500
                        )
                        b64_frame = base64.b64encode(screenshot_bytes).decode("utf-8")
                        for sub in list(self.frame_subscribers):
                            try:
                                res = sub(b64_frame)
                                if asyncio.iscoroutine(res):
                                    await res
                            except Exception as sub_err:
                                logger.debug(f"Frame subscriber error: {sub_err}")
                    except Exception as ex:
                        logger.debug(f"Screenshot capture skipped: {ex}")
                await asyncio.sleep(interval)

        self._stream_task = asyncio.create_task(_loop())

    async def stop_stream(self) -> None:
        """Halt viewport frame capture loop."""
        self.is_streaming = False
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None

    async def handle_remote_click(
        self, x: float, y: float, button: str = "left"
    ) -> None:
        """Dispatch remote mouse click to browser page."""
        page = self.page_provider()
        if not page:
            return
        await page.mouse.click(x, y, button=button)

    async def handle_remote_move(self, x: float, y: float) -> None:
        """Dispatch remote mouse movement to browser page."""
        page = self.page_provider()
        if not page:
            return
        await page.mouse.move(x, y)

    async def handle_remote_scroll(self, delta_x: float, delta_y: float) -> None:
        """Dispatch remote mouse scroll to browser page."""
        page = self.page_provider()
        if not page:
            return
        await page.mouse.wheel(delta_x, delta_y)

    async def handle_remote_type(self, text: str) -> None:
        """Dispatch remote text input to browser page."""
        page = self.page_provider()
        if not page:
            return
        await page.keyboard.type(text)

    async def handle_remote_press(self, key: str) -> None:
        """Dispatch remote key press (Enter, Backspace, Tab) to browser page."""
        page = self.page_provider()
        if not page:
            return
        await page.keyboard.press(key)
