"""Tests for Co-Pilot step approval and self-healing action recovery."""

import pytest
from browserpilot.agent.actions import ActionCommand, execute_action
from browserpilot.agent.models import LLMResponse
from browserpilot.agent.planner import AgentPlanner
from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.browser.stealth_context import BrowserManager
from browserpilot.config import Settings
from browserpilot.dom.a11y_tree import ActionableElement


class SingleStepMockLLM:
    """Mock LLM returning click action."""

    async def generate_action(self, *args, **kwargs) -> LLMResponse:
        return LLMResponse(
            content='{"action": "click", "element_id": 1, "reasoning": "Click primary button"}',
            parsed_json={"action": "click", "element_id": 1, "reasoning": "Click primary button"},
            prompt_tokens=100,
            completion_tokens=25,
            total_tokens=125,
            cost_usd=0.0001,
            latency_ms=15.0,
        )


@pytest.mark.asyncio
async def test_co_pilot_step_approval() -> None:
    """Verify that co_pilot_mode pauses before action execution until approval."""
    settings = Settings(headless=True)
    planner = AgentPlanner(goal="Approve step test", settings=settings, co_pilot_mode=True)
    planner.llm_client = SingleStepMockLLM()  # type: ignore

    approval_called = False

    async def mock_approval_callback(step):
        nonlocal approval_called
        approval_called = True
        # Immediately approve step
        planner.approve_step()

    planner.on_approval_callback = mock_approval_callback

    async with BrowserManager(settings) as bm:
        page = await bm.new_page()
        await page.set_content("<button id='b1'>Click Me</button>")

        step = await planner.step(page, bm.cursor, browser_manager=bm)
        assert approval_called is True
        assert step.step_number == 1
        assert step.action.action == "click"


@pytest.mark.asyncio
async def test_self_healing_click_dispatch() -> None:
    """Verify that force_dispatch or coordinate click fallback triggers DOM dispatch."""
    settings = Settings(headless=True)
    async with BrowserManager(settings) as bm:
        page = await bm.new_page()
        await page.set_content("""
        <html>
        <body>
            <button id="target" onclick="document.body.setAttribute('data-clicked', 'true')">Click</button>
        </body>
        </html>
        """)

        elem = ActionableElement(
            id=1,
            role="button",
            name="Click",
            x=20.0,
            y=20.0,
            width=80.0,
            height=30.0,
            tag="button",
        )

        cmd = ActionCommand(
            action="click",
            element_id=1,
            force_dispatch=True,  # Test self-healing JS path
            reasoning="Click target button",
        )

        result = await execute_action(cmd, page, {1: elem}, bm.cursor, bm)
        assert result["success"] is True

        attr = await page.get_attribute("body", "data-clicked")
        assert attr == "true"
