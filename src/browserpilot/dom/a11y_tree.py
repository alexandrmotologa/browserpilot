"""Accessibility tree parser extracting actionable nodes and formatting token-compact prompts."""

import json
import logging
from typing import Any
from pydantic import BaseModel, Field
from browserpilot.dom.spatial_matcher import ViewportBounds, is_element_visible

logger = logging.getLogger("browserpilot.dom")

# Client-side script scanning interactive accessibility candidates with viewport bounds
A11Y_EXTRACTION_SCRIPT = """
() => {
    const isVisible = (elem, rect) => {
        if (!rect || rect.width <= 2 || rect.height <= 2) return false;
        const style = window.getComputedStyle(elem);
        if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) < 0.05) {
            return false;
        }
        return true;
    };

    const getAccessibleName = (elem) => {
        let name = '';
        if (elem.getAttribute('aria-label')) {
            name = elem.getAttribute('aria-label').trim();
        } else if (elem.getAttribute('aria-labelledby')) {
            const labelled = document.getElementById(elem.getAttribute('aria-labelledby'));
            if (labelled) name = (labelled.innerText || labelled.textContent || '').trim();
        }
        if (!name && elem.placeholder) {
            name = elem.placeholder.trim();
        }
        if (!name && elem.title) {
            name = elem.title.trim();
        }
        if (!name && elem.alt) {
            name = elem.alt.trim();
        }
        if (!name && (elem.tagName === 'INPUT' || elem.tagName === 'BUTTON')) {
            name = (elem.value || '').trim();
        }
        if (!name) {
            name = (elem.innerText || elem.textContent || '').trim();
        }
        // Normalize whitespace and clamp length
        name = name.replace(/\\s+/g, ' ').slice(0, 80);
        return name;
    };

    const getElementRole = (elem) => {
        const explicitRole = elem.getAttribute('role');
        if (explicitRole) return explicitRole.toLowerCase();

        const tag = elem.tagName.toLowerCase();
        if (tag === 'a') return 'link';
        if (tag === 'button') return 'button';
        if (tag === 'select') return 'combobox';
        if (tag === 'textarea') return 'textbox';
        if (tag === 'input') {
            const type = (elem.type || 'text').toLowerCase();
            if (['button', 'submit', 'reset'].includes(type)) return 'button';
            if (type === 'checkbox') return 'checkbox';
            if (type === 'radio') return 'radio';
            return 'textbox';
        }
        if (elem.isContentEditable) return 'textbox';
        if (elem.hasAttribute('tabindex') && elem.getAttribute('tabindex') !== '-1') return 'button';
        if (elem.onclick || window.getComputedStyle(elem).cursor === 'pointer') return 'clickable';
        return tag;
    };

    const query = [
        'a[href]',
        'button:not([disabled])',
        'input:not([type="hidden"]):not([disabled])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        '[role="button"]',
        '[role="link"]',
        '[role="checkbox"]',
        '[role="radio"]',
        '[role="combobox"]',
        '[role="menuitem"]',
        '[role="tab"]',
        '[tabindex]:not([tabindex="-1"])',
        '[contenteditable="true"]',
        'summary'
    ].join(',');

    const rawCandidates = Array.from(document.querySelectorAll(query));
    const results = [];
    const seenRects = new Set();

    for (const elem of rawCandidates) {
        const rect = elem.getBoundingClientRect();
        if (!isVisible(elem, rect)) continue;

        // Skip duplicates that share exact coordinates (parent/child overlap)
        const key = `${Math.round(rect.left)},${Math.round(rect.top)},${Math.round(rect.width)},${Math.round(rect.height)}`;
        if (seenRects.has(key)) continue;
        seenRects.add(key);

        const role = getElementRole(elem);
        const name = getAccessibleName(elem);
        const isFocused = document.activeElement === elem;
        const isDisabled = elem.disabled || elem.getAttribute('aria-disabled') === 'true';

        let value = null;
        if (elem.tagName === 'INPUT' || elem.tagName === 'TEXTAREA' || elem.tagName === 'SELECT') {
            value = elem.value || null;
        }

        let isChecked = null;
        if (elem.type === 'checkbox' || elem.type === 'radio' || role === 'checkbox' || role === 'radio') {
            isChecked = elem.checked || elem.getAttribute('aria-checked') === 'true';
        }

        results.push({
            tag: elem.tagName.toLowerCase(),
            role: role,
            name: name,
            value: value,
            x: Math.round(rect.left),
            y: Math.round(rect.top),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            is_focused: isFocused,
            is_disabled: isDisabled,
            is_checked: isChecked
        });
    }

    // Sort by vertical position then horizontal position for natural reading order
    results.sort((a, b) => {
        if (Math.abs(a.y - b.y) > 15) {
            return a.y - b.y;
        }
        return a.x - b.x;
    });

    return results;
}
"""


class ActionableElement(BaseModel):
    """Represents a discovered interactive element on the page."""

    id: int = Field(description="Unique numeric badge index assigned to element")
    role: str = Field(description="Semantic role: button, link, textbox, combobox, etc.")
    name: str = Field(default="", description="Accessible label or visible text")
    value: str | None = Field(default=None, description="Current field value if applicable")
    x: float
    y: float
    width: float
    height: float
    tag: str
    is_focused: bool = False
    is_disabled: bool = False
    is_checked: bool | None = None

    @property
    def center_x(self) -> float:
        """Horizontal click coordinate."""
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        """Vertical click coordinate."""
        return self.y + (self.height / 2.0)

    def to_prompt_line(self) -> str:
        """Format node for inclusion in the compact LLM prompt."""
        flags: list[str] = []
        if self.is_focused:
            flags.append("focused")
        if self.is_checked is True:
            flags.append("checked")
        if self.is_checked is False:
            flags.append("unchecked")
        if self.value:
            # Shorten displayed value if long
            val_str = self.value if len(self.value) <= 25 else self.value[:22] + "..."
            flags.append(f'val="{val_str}"')

        flag_str = f" [{', '.join(flags)}]" if flags else ""
        label = f'"{self.name}"' if self.name else ""

        return (
            f"[{self.id}] {self.role} {label} "
            f"(x:{int(self.center_x)}, y:{int(self.center_y)}){flag_str}".strip()
        )


class AccessibilityTreeParser:
    """Extracts, filters, and formats actionable accessibility nodes from a live page."""

    @staticmethod
    async def parse_page(
        page: Any,
        viewport_width: float = 1280.0,
        viewport_height: float = 800.0,
        max_elements: int = 120,
    ) -> list[ActionableElement]:
        """Scan active page and return indexed list of actionable elements."""
        try:
            raw_elements = await page.evaluate(A11Y_EXTRACTION_SCRIPT)
        except Exception as ex:
            logger.error(f"Error evaluating accessibility script: {ex}")
            return []

        elements: list[ActionableElement] = []
        element_id = 1

        for raw in raw_elements:
            bounds = ViewportBounds(
                x=float(raw["x"]),
                y=float(raw["y"]),
                width=float(raw["width"]),
                height=float(raw["height"]),
            )

            # Ensure element is visible in viewport space
            if not is_element_visible(bounds, viewport_width, viewport_height):
                continue

            elem = ActionableElement(
                id=element_id,
                role=raw.get("role", "clickable"),
                name=raw.get("name", "").strip(),
                value=raw.get("value"),
                x=bounds.x,
                y=bounds.y,
                width=bounds.width,
                height=bounds.height,
                tag=raw.get("tag", "div"),
                is_focused=bool(raw.get("is_focused", False)),
                is_disabled=bool(raw.get("is_disabled", False)),
                is_checked=raw.get("is_checked"),
            )
            elements.append(elem)
            element_id += 1

            if len(elements) >= max_elements:
                break

        return elements

    @staticmethod
    def format_prompt_tree(elements: list[ActionableElement]) -> str:
        """Generate structured text representation reducing prompt tokens by ~80%."""
        if not elements:
            return "No interactive elements detected on current viewport."

        lines = [elem.to_prompt_line() for elem in elements]
        return "\n".join(lines)
