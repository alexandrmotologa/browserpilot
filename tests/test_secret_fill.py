"""Tests for secure credential auto-fill without LLM exposure."""

import os
import pytest
from browserpilot.agent.actions import ActionCommand, execute_action
from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.browser.stealth_context import BrowserManager
from browserpilot.config import Settings
from browserpilot.dom.a11y_tree import ActionableElement


@pytest.mark.asyncio
async def test_fill_secret_secure_injection() -> None:
    """Verify fill_secret retrieves environment variable and types without prompt leakage."""
    os.environ["TEST_VAULT_PASSWORD"] = "SuperSecret123!"

    settings = Settings(headless=True)
    async with BrowserManager(settings) as bm:
        page = await bm.new_page()
        await page.set_content("""
        <html>
        <body>
            <input id="pwd-field" type="password" />
        </body>
        </html>
        """)

        elem = ActionableElement(
            id=1,
            role="textbox",
            name="password",
            x=50.0,
            y=50.0,
            width=150.0,
            height=30.0,
            tag="input",
        )

        cmd = ActionCommand(
            action="fill_secret",
            element_id=1,
            secret_key="TEST_VAULT_PASSWORD",
            reasoning="Inject account password",
        )

        result = await execute_action(
            command=cmd,
            page=page,
            elements={1: elem},
            cursor=bm.cursor,
        )

        assert result["success"] is True
        assert "SuperSecret123!" not in result["detail"]  # Value masked in logs

        # Verify page input actually received the real secret
        val = await page.input_value("#pwd-field")
        assert val == "SuperSecret123!"
