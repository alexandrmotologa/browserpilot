"""End-to-end integration tests verifying agent loop and DOM interactions."""

import pytest
from browserpilot.agent.actions import ActionCommand
from browserpilot.agent.models import LLMResponse
from browserpilot.agent.planner import AgentPlanner
from browserpilot.browser.stealth_context import BrowserManager
from browserpilot.config import Settings


class MockLLMClient:
    """Mock LLM generating predetermined actions for deterministic integration testing."""

    def __init__(self, actions: list[dict]) -> None:
        self.actions = actions
        self.call_count = 0

    async def generate_action(
        self,
        system_prompt: str,
        user_prompt: str,
        override_model: str | None = None,
    ) -> LLMResponse:
        idx = min(self.call_count, len(self.actions) - 1)
        action_payload = self.actions[idx]
        self.call_count += 1

        return LLMResponse(
            content=str(action_payload),
            parsed_json=action_payload,
            prompt_tokens=150,
            completion_tokens=40,
            total_tokens=190,
            cost_usd=0.0001,
            latency_ms=25.0,
        )


@pytest.mark.asyncio
async def test_agent_multi_step_flow() -> None:
    """Verify agent navigates page, types in input, clicks button, and finishes."""
    test_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>BrowserPilot Testbed</h1>
        <input id="test-input" placeholder="Type here..." />
        <button id="test-btn" onclick="document.getElementById('status').innerText = 'Submitted: ' + document.getElementById('test-input').value">Submit</button>
        <div id="status">Waiting</div>
    </body>
    </html>
    """

    mock_actions = [
        {
            "action": "type",
            "element_id": 1,
            "text": "Hello Autonomous World",
            "press_enter": False,
            "reasoning": "Type greeting into text input",
        },
        {
            "action": "click",
            "element_id": 2,
            "reasoning": "Click submit button",
        },
        {
            "action": "finish",
            "reasoning": "Goal accomplished",
            "answer": "Form was successfully filled and submitted",
        },
    ]

    settings = Settings(headless=True)
    planner = AgentPlanner(goal="Submit test form", settings=settings)
    # Inject mock LLM
    planner.llm_client = MockLLMClient(mock_actions)  # type: ignore

    async with BrowserManager(settings) as bm:
        page = await bm.new_page()
        await page.set_content(test_html)

        steps = await planner.run(page, bm.cursor, max_steps=5)

        assert len(steps) == 3
        assert planner.is_done is True
        assert planner.final_answer == "Form was successfully filled and submitted"

        # Verify DOM mutation took effect in browser page
        status_text = await page.inner_text("#status")
        assert "Submitted: Hello Autonomous World" in status_text
