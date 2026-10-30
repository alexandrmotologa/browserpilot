"""Action models and executors for dispatching user and agent browser interactions."""

import asyncio
import logging
import random
from typing import Any, Literal
from pydantic import BaseModel, Field
from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.dom.a11y_tree import ActionableElement

logger = logging.getLogger("browserpilot.agent.actions")

ActionType = Literal[
    "click",
    "type",
    "press_key",
    "scroll",
    "select",
    "wait",
    "goto",
    "finish",
    "fail",
]


class ActionCommand(BaseModel):
    """Structured action instruction emitted by the planner."""

    action: ActionType = Field(description="Action verb to execute")
    element_id: int | None = Field(
        default=None,
        description="Numeric badge identifier of the target element",
    )
    text: str | None = Field(
        default=None,
        description="Text content to type into an input field",
    )
    key: str | None = Field(
        default=None,
        description="Keyboard key to press (Enter, Tab, Escape, etc.)",
    )
    press_enter: bool = Field(
        default=False,
        description="Automatically press Enter key after typing",
    )
    direction: Literal["up", "down"] | None = Field(
        default=None,
        description="Scroll direction",
    )
    amount: int | None = Field(
        default=None,
        description="Scroll pixel distance",
    )
    url: str | None = Field(
        default=None,
        description="Target destination URL for goto actions",
    )
    seconds: float | None = Field(
        default=None,
        description="Duration to wait in seconds",
    )
    reasoning: str = Field(
        default="",
        description="Self-reflective reasoning justifying the chosen action",
    )
    answer: str | None = Field(
        default=None,
        description="Final answer or extracted data upon completing the mission",
    )


async def execute_action(
    command: ActionCommand,
    page: Any,
    elements: dict[int, ActionableElement],
    cursor: CursorMotion,
) -> dict[str, Any]:
    """Dispatch the given action command to the active browser page."""
    action = command.action

    if action == "goto":
        if not command.url:
            raise ValueError("URL must be provided for 'goto' action")
        target_url = command.url if command.url.startswith("http") else f"https://{command.url}"
        await page.goto(target_url, wait_until="domcontentloaded")
        await asyncio.sleep(1.0)
        return {"success": True, "detail": f"Navigated to {target_url}"}

    if action == "click":
        if command.element_id is None:
            raise ValueError("element_id is required for 'click' action")
        elem = elements.get(command.element_id)
        if not elem:
            raise KeyError(f"Element ID [{command.element_id}] not found on page")

        await cursor.click_at(page, elem.center_x, elem.center_y)
        await asyncio.sleep(0.5)
        return {
            "success": True,
            "detail": f"Clicked [{elem.id}] {elem.role} '{elem.name}' at ({int(elem.center_x)}, {int(elem.center_y)})",
        }

    if action == "type":
        if command.element_id is None:
            raise ValueError("element_id is required for 'type' action")
        if command.text is None:
            raise ValueError("text must be provided for 'type' action")

        elem = elements.get(command.element_id)
        if not elem:
            raise KeyError(f"Element ID [{command.element_id}] not found on page")

        # Focus element with natural click
        await cursor.click_at(page, elem.center_x, elem.center_y)
        await asyncio.sleep(0.15)

        # Clear existing text if any
        await page.keyboard.press("ControlOrMeta+A")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.05)

        # Type with randomized inter-keystroke delays
        for char in command.text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.015, 0.055))

        if command.press_enter:
            await asyncio.sleep(random.uniform(0.1, 0.25))
            await page.keyboard.press("Enter")

        return {
            "success": True,
            "detail": f"Typed '{command.text}' into [{elem.id}] {elem.role}",
        }

    if action == "press_key":
        key = command.key or "Enter"
        await page.keyboard.press(key)
        return {"success": True, "detail": f"Pressed key '{key}'"}

    if action == "scroll":
        direction = command.direction or "down"
        distance = command.amount or 450
        delta_y = distance if direction == "down" else -distance
        await page.mouse.wheel(0, delta_y)
        await asyncio.sleep(0.6)
        return {"success": True, "detail": f"Scrolled {direction} by {distance}px"}

    if action == "select":
        if command.element_id is None:
            raise ValueError("element_id is required for 'select' action")
        elem = elements.get(command.element_id)
        if not elem:
            raise KeyError(f"Element ID [{command.element_id}] not found on page")

        # Click to open dropdown or dispatch change
        await cursor.click_at(page, elem.center_x, elem.center_y)
        if command.text:
            await page.keyboard.type(command.text)
            await page.keyboard.press("Enter")
        return {"success": True, "detail": f"Selected value on [{elem.id}]"}

    if action == "wait":
        duration = command.seconds or 2.0
        await asyncio.sleep(duration)
        return {"success": True, "detail": f"Waited for {duration}s"}

    if action in ("finish", "fail"):
        return {
            "success": action == "finish",
            "is_terminal": True,
            "detail": command.answer or command.reasoning,
        }

    raise ValueError(f"Unknown action type: {action}")
