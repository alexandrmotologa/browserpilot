"""Autonomous Observe-Reason-Act-Verify agent execution loop with Co-Pilot and Multi-Tab support."""

import asyncio
import base64
import logging
import uuid
from typing import Any, Callable, Coroutine
from pydantic import BaseModel, Field
from browserpilot.agent.actions import ActionCommand, execute_action
from browserpilot.agent.models import LLMClient, LLMResponse
from browserpilot.agent.verifier import ActionVerifier, VerificationResult
from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.config import Settings, get_settings
from browserpilot.dom.a11y_tree import AccessibilityTreeParser, ActionableElement
from browserpilot.dom.element_highlighter import ElementHighlighter
from browserpilot.human.captcha_detector import CaptchaDetector

logger = logging.getLogger("browserpilot.agent.planner")

SYSTEM_PROMPT = """You are BrowserPilot, an autonomous browser navigation agent.
Your objective is to accomplish the user's goal on the web accurately and efficiently.

You receive:
1. Current page URL and Title
2. List of interactive elements parsed from the accessibility tree in the format:
   [<id>] <role> "<name>" (x:<center_x>, y:<center_y>) [<flags>]
3. Currently open browser tabs (if more than 1)
4. History of previous actions

OUTPUT RULES:
Output only a valid JSON object matching this schema without extra conversational filler:
{
  "action": "click" | "type" | "fill_secret" | "press_key" | "scroll" | "select" | "wait" | "goto" | "switch_tab" | "new_tab" | "close_tab" | "extract_data" | "finish" | "fail",
  "element_id": <integer id of target element or null>,
  "text": "<text to type if action is type or null>",
  "secret_key": "<name of environment variable if action is fill_secret or null>",
  "press_enter": <true if Enter should be pressed after typing, else false>,
  "key": "<key name like Enter, Tab, Escape if action is press_key or null>",
  "direction": "up" | "down" | null,
  "amount": <number of pixels to scroll, e.g. 450, or null>,
  "url": "<destination URL if action is goto or new_tab or null>",
  "tab_index": <integer tab index to switch to or close, or null>,
  "seconds": <duration to wait if action is wait or null>,
  "extracted_data": <structured json object or list of objects if action is extract_data or null>,
  "reasoning": "<concise explanation of why this step was chosen>",
  "answer": "<final answer or task summary when action is finish or null>"
}

STRATEGY GUIDELINES:
- Target elements using their numeric id: "element_id": 14.
- If entering a password or sensitive API key, use "action": "fill_secret" with "secret_key": "ENV_VAR_NAME".
- If an input field requires typing and submitting, you may set "press_enter": true.
- If multiple tabs are open and relevant content or popup is in another tab, use "action": "switch_tab" with "tab_index".
- To extract structured datasets (tables, product cards, pricing), use "action": "extract_data" with "extracted_data": [...].
- If you do not see the target on the screen, use action "scroll" with direction "down".
- If a cookie banner or modal blocks your progress, click its accept or dismiss button first.
- When the goal is completed, output "action": "finish" and provide the answer or result in "answer".
"""


class AgentStep(BaseModel):
    """Snapshot record of an individual execution cycle."""

    step_number: int
    url: str
    title: str
    thought: str
    action: ActionCommand
    verification: VerificationResult | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    screenshot_base64: str | None = None


class AgentPlanner:
    """Coordinates the autonomous navigation loop across browser pages."""

    def __init__(
        self,
        goal: str,
        settings: Settings | None = None,
        co_pilot_mode: bool = False,
        on_step_callback: Callable[[AgentStep], Coroutine[Any, Any, None]] | None = None,
        on_takeover_callback: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        on_approval_callback: Callable[[AgentStep], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self.session_id: str = f"sess_{uuid.uuid4().hex[:8]}"
        self.goal: str = goal
        self.settings: Settings = settings or get_settings()
        self.co_pilot_mode: bool = co_pilot_mode
        self.llm_client: LLMClient = LLMClient(self.settings)
        self.steps: list[AgentStep] = []
        self.on_step_callback = on_step_callback
        self.on_takeover_callback = on_takeover_callback
        self.on_approval_callback = on_approval_callback

        self.is_paused: bool = False
        self.is_stopped: bool = False
        self.is_done: bool = False
        self.takeover_required: bool = False
        self.awaiting_approval: bool = False
        self.final_answer: str | None = None
        self.extracted_data: list[dict[str, Any]] | dict[str, Any] | None = None

        self._approval_event = asyncio.Event()
        self._approved_command_override: ActionCommand | None = None

        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0

    async def pause(self) -> None:
        """Pause agent execution loop."""
        self.is_paused = True
        logger.info(f"Session {self.session_id} paused")

    async def resume(self) -> None:
        """Resume agent execution loop."""
        self.is_paused = False
        self.takeover_required = False
        logger.info(f"Session {self.session_id} resumed")

    async def stop(self) -> None:
        """Abort agent execution loop."""
        self.is_stopped = True
        self._approval_event.set()
        logger.info(f"Session {self.session_id} stopped")

    def approve_step(self, modified_command: ActionCommand | None = None) -> None:
        """Approve proposed step in Co-Pilot mode, optionally with operator modifications."""
        self._approved_command_override = modified_command
        self.awaiting_approval = False
        self._approval_event.set()

    def _build_user_prompt(
        self,
        url: str,
        title: str,
        a11y_tree_text: str,
        tabs: list[dict[str, Any]],
    ) -> str:
        """Construct prompt containing mission context, history, tabs, and accessibility tree."""
        history_lines: list[str] = []
        recent_steps = self.steps[-4:] if len(self.steps) > 4 else self.steps
        for s in recent_steps:
            history_lines.append(
                f"- Step {s.step_number}: Action={s.action.action} (target={s.action.element_id}) -> Thought: {s.thought}"
            )

        history_section = (
            "\n".join(history_lines) if history_lines else "None (initial step)"
        )

        tabs_section = ""
        if len(tabs) > 1:
            tab_lines = [
                f"[{t['index']}] \"{t['title']}\" ({t['url']}){' [ACTIVE]' if t['is_active'] else ''}"
                for t in tabs
            ]
            tabs_section = "OPEN BROWSER TABS:\n" + "\n".join(tab_lines) + "\n\n"

        return (
            f"GOAL: {self.goal}\n\n"
            f"CURRENT PAGE:\n"
            f"- URL: {url}\n"
            f"- Title: {title}\n\n"
            f"{tabs_section}"
            f"PREVIOUS ACTIONS:\n{history_section}\n\n"
            f"ACCESSIBILITY INTERACTIVE ELEMENTS:\n"
            f"{a11y_tree_text}\n\n"
            f"Decide your next action. Return JSON only."
        )

    async def step(
        self,
        page: Any,
        cursor: CursorMotion,
        browser_manager: Any = None,
    ) -> AgentStep:
        """Execute one complete Observe-Reason-Act-Verify cycle."""
        step_num = len(self.steps) + 1
        url = page.url
        title = await page.title()

        # 1. Parse accessibility elements
        elements = await AccessibilityTreeParser.parse_page(
            page,
            viewport_width=self.settings.viewport_width,
            viewport_height=self.settings.viewport_height,
        )
        elements_map = {el.id: el for el in elements}
        a11y_text = AccessibilityTreeParser.format_prompt_tree(elements)

        # 2. Inject ephemeral visual badges
        badge_data = [{"id": el.id, "x": el.x, "y": el.y} for el in elements]
        await ElementHighlighter.inject_badges(page, badge_data)

        # 3. Check for CAPTCHA or 2FA hurdles
        if self.settings.enable_human_takeover:
            challenge = await CaptchaDetector.detect(page)
            if challenge.is_detected:
                self.takeover_required = True
                self.is_paused = True
                if self.on_takeover_callback:
                    await self.on_takeover_callback(challenge.challenge_type)
                logger.warning(
                    f"Human takeover required: {challenge.challenge_type} ({challenge.description})"
                )

        # 4. Capture screenshot frame for live stream and telemetry
        screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        # 5. Query open tabs if browser_manager available
        tabs: list[dict[str, Any]] = []
        if browser_manager:
            tabs = await browser_manager.get_tabs()

        # 6. Reason via LLM
        prompt = self._build_user_prompt(url, title, a11y_text, tabs)
        llm_response: LLMResponse = await self.llm_client.generate_action(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        # 7. Clear visual badges from DOM
        await ElementHighlighter.clear_badges(page)

        # Parse command
        parsed = llm_response.parsed_json
        command = ActionCommand(
            action=parsed.get("action", "wait"),
            element_id=parsed.get("element_id"),
            text=parsed.get("text"),
            secret_key=parsed.get("secret_key"),
            key=parsed.get("key"),
            press_enter=bool(parsed.get("press_enter", False)),
            direction=parsed.get("direction"),
            amount=parsed.get("amount"),
            url=parsed.get("url"),
            tab_index=parsed.get("tab_index"),
            seconds=parsed.get("seconds"),
            force_dispatch=bool(parsed.get("force_dispatch", False)),
            extracted_data=parsed.get("extracted_data"),
            reasoning=parsed.get("reasoning", ""),
            answer=parsed.get("answer"),
        )

        # 8. Co-Pilot Mode: Await operator approval if enabled
        if self.co_pilot_mode:
            self.awaiting_approval = True
            self._approval_event.clear()
            self._approved_command_override = None

            temp_step = AgentStep(
                step_number=step_num,
                url=page.url,
                title=title,
                thought=command.reasoning,
                action=command,
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
                cost_usd=llm_response.cost_usd,
                latency_ms=llm_response.latency_ms,
                screenshot_base64=screenshot_b64,
            )

            if self.on_approval_callback:
                await self.on_approval_callback(temp_step)

            logger.info(f"Co-Pilot: Awaiting operator approval for Step {step_num}...")
            await self._approval_event.wait()

            if self._approved_command_override is not None:
                command = self._approved_command_override
                logger.info(f"Co-Pilot: Executing modified command: {command.action}")

        target_el = elements_map.get(command.element_id) if command.element_id else None

        # 9. Act
        prev_url = page.url
        try:
            await execute_action(
                command,
                page,
                elements_map,
                cursor,
                browser_manager=browser_manager,
            )
        except Exception as ex:
            logger.error(f"Action execution error on step {step_num}: {ex}")

        # 10. Verify
        verification = await ActionVerifier.verify(
            page=page,
            previous_url=prev_url,
            command=command,
            target_element=target_el,
        )

        if command.action == "finish":
            self.is_done = True
            self.final_answer = command.answer or command.reasoning
        elif command.action == "extract_data":
            self.is_done = True
            self.extracted_data = command.extracted_data
            self.final_answer = f"Structured data extracted successfully ({len(command.extracted_data) if isinstance(command.extracted_data, list) else 1} items)"
        elif command.action == "fail":
            self.is_done = True
            self.is_stopped = True

        # Accumulate metrics
        self.total_prompt_tokens += llm_response.prompt_tokens
        self.total_completion_tokens += llm_response.completion_tokens
        self.total_cost_usd += llm_response.cost_usd

        step_record = AgentStep(
            step_number=step_num,
            url=page.url,
            title=await page.title(),
            thought=command.reasoning,
            action=command,
            verification=verification,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            cost_usd=llm_response.cost_usd,
            latency_ms=llm_response.latency_ms,
            screenshot_base64=screenshot_b64,
        )

        self.steps.append(step_record)

        if self.on_step_callback:
            await self.on_step_callback(step_record)

        return step_record

    async def run(
        self,
        page: Any,
        cursor: CursorMotion,
        start_url: str | None = None,
        max_steps: int | None = None,
        browser_manager: Any = None,
    ) -> list[AgentStep]:
        """Execute the autonomous mission until completion or step limit."""
        limit = max_steps or self.settings.max_steps

        if start_url:
            target = start_url if start_url.startswith("http") else f"https://{start_url}"
            await page.goto(target, wait_until="domcontentloaded")
            await asyncio.sleep(1.0)

        while len(self.steps) < limit and not self.is_done and not self.is_stopped:
            # Handle paused state (including human takeover)
            while self.is_paused and not self.is_stopped:
                await asyncio.sleep(0.5)

            if self.is_stopped:
                break

            # If multi-tab switched the active page, target the current active page
            target_page = browser_manager.active_page if browser_manager and browser_manager.active_page else page
            await self.step(target_page, cursor, browser_manager=browser_manager)
            await asyncio.sleep(0.5)

        return self.steps
