"""Action models and executors for dispatching user and agent browser interactions with self-healing."""

import asyncio
import logging
import os
import random
from typing import Any, Literal
from pydantic import BaseModel, Field
from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.dom.a11y_tree import ActionableElement

logger = logging.getLogger("browserpilot.agent.actions")

ActionType = Literal[
    "click",
    "type",
    "fill_secret",
    "press_key",
    "scroll",
    "select",
    "wait",
    "goto",
    "switch_tab",
    "new_tab",
    "close_tab",
    "extract_data",
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
    secret_key: str | None = Field(
        default=None,
        description="Environment variable key for safe credential auto-fill",
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
    tab_index: int | None = Field(
        default=None,
        description="Target browser tab index for multi-tab operations",
    )
    seconds: float | None = Field(
        default=None,
        description="Duration to wait in seconds",
    )
    force_dispatch: bool = Field(
        default=False,
        description="Force direct JavaScript DOM event dispatch as self-healing fallback",
    )
    extracted_data: list[dict[str, Any]] | dict[str, Any] | None = Field(
        default=None,
        description="Structured data extracted from the page",
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
    browser_manager: Any = None,
) -> dict[str, Any]:
    """Dispatch the given action command to the active browser page with self-healing recovery."""
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

        # 1. Standard humanized Bézier motion and click
        click_error = None
        try:
            await cursor.click_at(page, elem.center_x, elem.center_y)
        except Exception as ex:
            click_error = ex
            logger.warning(
                f"Standard click at ({int(elem.center_x)}, {int(elem.center_y)}) encountered error: {ex}. Applying self-healing fallback..."
            )

        # 2. Self-healing fallback: scroll into view and trigger JavaScript click dispatch
        if click_error is not None or command.force_dispatch:
            try:
                await page.evaluate(
                    """({x, y, name, tag}) => {
                        let target = document.elementFromPoint(x, y);
                        if (!target || target === document.body || target === document.documentElement) {
                            if (name) {
                                target = Array.from(document.querySelectorAll(tag || '*')).find(
                                    el => (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim() === name
                                );
                            }
                            if (!target && tag) {
                                target = document.querySelector(tag);
                            }
                        }
                        if (target) {
                            target.scrollIntoView({ behavior: 'instant', block: 'center' });
                            target.click();
                            target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        }
                    }""",
                    {"x": elem.center_x, "y": elem.center_y, "name": elem.name, "tag": elem.tag},
                )
                logger.info(f"Self-healing fallback dispatched click for [{elem.id}]")
            except Exception as js_ex:
                logger.error(f"Self-healing DOM dispatch failed: {js_ex}")
                if click_error is not None:
                    raise click_error

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

        # Focus element with natural click and ensure focus
        await cursor.click_at(page, elem.center_x, elem.center_y)
        await asyncio.sleep(0.15)
        await page.evaluate(
            """({x, y, tag}) => {
                let target = document.elementFromPoint(x, y);
                if (!target || target === document.body) {
                    target = document.querySelector(tag || 'input') || document.querySelector('input, textarea');
                }
                if (target) target.focus();
            }""",
            {"x": elem.center_x, "y": elem.center_y, "tag": elem.tag},
        )

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

    if action == "fill_secret":
        if command.element_id is None:
            raise ValueError("element_id is required for 'fill_secret' action")
        if not command.secret_key:
            raise ValueError("secret_key must be provided for 'fill_secret' action")

        secret_value = os.getenv(command.secret_key, "")
        if not secret_value:
            raise ValueError(f"Secret variable '{command.secret_key}' is not set in environment")

        elem = elements.get(command.element_id)
        if not elem:
            raise KeyError(f"Element ID [{command.element_id}] not found on page")

        await cursor.click_at(page, elem.center_x, elem.center_y)
        await asyncio.sleep(0.15)
        await page.evaluate(
            """({x, y, tag}) => {
                let target = document.elementFromPoint(x, y);
                if (!target || target === document.body) {
                    target = document.querySelector(tag || 'input') || document.querySelector('input, textarea');
                }
                if (target) target.focus();
            }""",
            {"x": elem.center_x, "y": elem.center_y, "tag": elem.tag},
        )
        await page.keyboard.press("ControlOrMeta+A")
        await page.keyboard.press("Backspace")

        for char in secret_value:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.015, 0.045))

        if command.press_enter:
            await asyncio.sleep(0.15)
            await page.keyboard.press("Enter")

        return {
            "success": True,
            "detail": f"Safely injected secret '{command.secret_key}' into [{elem.id}] (value hidden)",
        }

    if action == "switch_tab":
        if browser_manager is None:
            raise RuntimeError("Browser manager is required for switch_tab action")
        target_idx = command.tab_index if command.tab_index is not None else 0
        new_active = await browser_manager.switch_tab(target_idx)
        return {
            "success": True,
            "detail": f"Switched to tab {target_idx} ({new_active.url})",
        }

    if action == "new_tab":
        if browser_manager is None:
            raise RuntimeError("Browser manager is required for new_tab action")
        new_page = await browser_manager.new_tab(command.url)
        return {
            "success": True,
            "detail": f"Opened new tab ({new_page.url})",
        }

    if action == "close_tab":
        if browser_manager is None:
            raise RuntimeError("Browser manager is required for close_tab action")
        await browser_manager.close_tab(command.tab_index)
        return {
            "success": True,
            "detail": "Closed browser tab",
        }

    if action == "extract_data":
        if not command.extracted_data:
            raise ValueError("extracted_data payload is required for 'extract_data' action")
        return {
            "success": True,
            "is_terminal": True,
            "detail": f"Extracted structured dataset ({len(command.extracted_data) if isinstance(command.extracted_data, list) else 1} records)",
            "data": command.extracted_data,
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
