"""Injects and clears ephemeral numeric visual badges directly on actionable DOM elements."""

from typing import Any

HIGHLIGHT_INJECTION_SCRIPT = """
(elements) => {
    // 1. Remove any previous badges
    const existingContainer = document.getElementById('__browserpilot_badge_container__');
    if (existingContainer) {
        existingContainer.remove();
    }

    const container = document.createElement('div');
    container.id = '__browserpilot_badge_container__';
    container.style.position = 'fixed';
    container.style.top = '0px';
    container.style.left = '0px';
    container.style.width = '100vw';
    container.style.height = '100vh';
    container.style.pointerEvents = 'none';
    container.style.zIndex = '2147483647';

    elements.forEach(item => {
        const badge = document.createElement('div');
        badge.className = '__browserpilot_badge__';
        badge.textContent = item.id;
        badge.style.position = 'absolute';
        badge.style.left = `${Math.max(0, item.x)}px`;
        badge.style.top = `${Math.max(0, item.y)}px`;
        badge.style.background = '#0f172a';
        badge.style.color = '#38bdf8';
        badge.style.border = '1px solid #38bdf8';
        badge.style.borderRadius = '3px';
        badge.style.padding = '1px 3px';
        badge.style.fontSize = '10px';
        badge.style.fontWeight = 'bold';
        badge.style.fontFamily = 'monospace';
        badge.style.lineHeight = '1';
        badge.style.boxShadow = '0 1px 3px rgba(0,0,0,0.6)';
        badge.style.pointerEvents = 'none';
        badge.style.transform = 'translate(-20%, -50%)';

        container.appendChild(badge);
    });

    document.documentElement.appendChild(container);
}
"""

REMOVE_HIGHLIGHT_SCRIPT = """
() => {
    const existing = document.getElementById('__browserpilot_badge_container__');
    if (existing) {
        existing.remove();
    }
}
"""


class ElementHighlighter:
    """Manages ephemeral visual badges overlaid on interactive targets in the browser."""

    @staticmethod
    async def inject_badges(page: Any, elements: list[dict[str, Any]]) -> None:
        """Render numeric badges matching element IDs onto the active page viewport."""
        badge_payload = [
            {"id": el["id"], "x": el["x"], "y": el["y"]}
            for el in elements
        ]
        await page.evaluate(HIGHLIGHT_INJECTION_SCRIPT, badge_payload)

    @staticmethod
    async def clear_badges(page: Any) -> None:
        """Remove all ephemeral visual badge elements from the DOM."""
        await page.evaluate(REMOVE_HIGHLIGHT_SCRIPT)
