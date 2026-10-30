"""Tests for multi-tab browser context management and tab switching."""

import pytest
from browserpilot.browser.stealth_context import BrowserManager
from browserpilot.config import Settings


@pytest.mark.asyncio
async def test_multi_tab_lifecycle() -> None:
    """Verify opening new tabs, listing them, switching, and closing."""
    settings = Settings(headless=True)
    async with BrowserManager(settings) as bm:
        # Initial page
        p1 = await bm.new_page()
        await p1.set_content("<html><head><title>Tab 1</title></head><body><h1>Tab 1</h1></body></html>")

        tabs_initial = await bm.get_tabs()
        assert len(tabs_initial) == 1
        assert tabs_initial[0]["title"] == "Tab 1"
        assert tabs_initial[0]["is_active"] is True

        # Open secondary tab
        p2 = await bm.new_tab()
        await p2.set_content("<html><head><title>Tab 2</title></head><body><h1>Tab 2</h1></body></html>")

        tabs_after = await bm.get_tabs()
        assert len(tabs_after) == 2
        assert tabs_after[1]["title"] == "Tab 2"
        assert tabs_after[1]["is_active"] is True

        # Switch back to Tab 1
        await bm.switch_tab(0)
        assert bm.active_page == p1

        # Close Tab 2
        await bm.close_tab(1)
        tabs_final = await bm.get_tabs()
        assert len(tabs_final) == 1
        assert tabs_final[0]["title"] == "Tab 1"
