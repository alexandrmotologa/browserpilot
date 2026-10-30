"""Tests for action command schema validation and JSON extraction heuristics."""

import pytest
from browserpilot.agent.actions import ActionCommand
from browserpilot.agent.models import compute_cost, extract_json_from_text


def test_action_command_parsing() -> None:
    """Validate ActionCommand field assignments and defaults."""
    cmd = ActionCommand(
        action="click",
        element_id=14,
        reasoning="Click checkout button to initiate order",
    )
    assert cmd.action == "click"
    assert cmd.element_id == 14
    assert cmd.press_enter is False


def test_extract_json_from_markdown_block() -> None:
    """Verify parsing when LLM surrounds payload in markdown fences."""
    raw = """
    Here is the next action to take:
    ```json
    {
      "action": "type",
      "element_id": 2,
      "text": "mechanical keyboard",
      "press_enter": true,
      "reasoning": "Enter search query"
    }
    ```
    """
    parsed = extract_json_from_text(raw)
    assert parsed["action"] == "type"
    assert parsed["element_id"] == 2
    assert parsed["text"] == "mechanical keyboard"
    assert parsed["press_enter"] is True


def test_compute_cost_model_pricing() -> None:
    """Verify token pricing arithmetic."""
    cost_gpt4o = compute_cost("gpt-4o", prompt_tokens=1000, completion_tokens=200)
    assert cost_gpt4o > 0.0

    cost_mini = compute_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=200)
    assert cost_mini < cost_gpt4o
