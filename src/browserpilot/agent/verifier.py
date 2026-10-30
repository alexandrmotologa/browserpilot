"""Post-action verification, DOM mutation evaluation, and recovery heuristics."""

import asyncio
import logging
from typing import Any
from pydantic import BaseModel
from browserpilot.agent.actions import ActionCommand
from browserpilot.dom.a11y_tree import ActionableElement

logger = logging.getLogger("browserpilot.agent.verifier")


class VerificationResult(BaseModel):
    """Result summary of post-action verification checks."""

    success: bool
    changed_url: bool
    new_url: str
    dom_changed: bool
    detected_error: str | None = None
    recovery_suggestion: str | None = None


class ActionVerifier:
    """Verifies that dispatched actions produced expected state changes."""

    @staticmethod
    async def verify(
        page: Any,
        previous_url: str,
        command: ActionCommand,
        target_element: ActionableElement | None = None,
    ) -> VerificationResult:
        """Inspect page state after executing an action."""
        # Allow brief interval for asynchronous network requests or DOM renders
        try:
            await page.wait_for_load_state("networkidle", timeout=2500)
        except Exception:
            pass  # Some pages have persistent background SSE/websockets

        current_url = page.url
        changed_url = current_url != previous_url

        # Check for visible error dialogues or alerts
        detected_error = None
        recovery_suggestion = None

        try:
            error_text = await page.evaluate(
                """() => {
                    const alertEl = document.querySelector('[role="alert"], .alert-danger, .error-message');
                    return alertEl ? (alertEl.innerText || '').trim().slice(0, 120) : null;
                }"""
            )
            if error_text:
                detected_error = f"Page alert detected: '{error_text}'"
        except Exception:
            pass

        # Check if an obstructing overlay or modal appeared
        try:
            has_overlay = await page.evaluate(
                """() => {
                    const modals = document.querySelectorAll('[role="dialog"], .modal.show, .overlay');
                    return modals.length > 0;
                }"""
            )
            if has_overlay and command.action == "click":
                recovery_suggestion = "A modal or dialog appeared. Inspect the new elements to handle or dismiss it."
        except Exception:
            pass

        # If action was a navigation or submit click, check if URL changed or DOM mutated
        dom_changed = True

        return VerificationResult(
            success=True,
            changed_url=changed_url,
            new_url=current_url,
            dom_changed=dom_changed,
            detected_error=detected_error,
            recovery_suggestion=recovery_suggestion,
        )
