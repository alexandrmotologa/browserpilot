"""DOM inspection, accessibility tree extraction, and visual badge grounding."""

from browserpilot.dom.a11y_tree import AccessibilityTreeParser, ActionableElement
from browserpilot.dom.element_highlighter import ElementHighlighter
from browserpilot.dom.spatial_matcher import ViewportBounds, is_element_visible

__all__ = [
    "AccessibilityTreeParser",
    "ActionableElement",
    "ElementHighlighter",
    "ViewportBounds",
    "is_element_visible",
]
