"""Tests for accessibility tree element extraction, spatial bounds, and prompt formatting."""

import pytest
from browserpilot.dom.a11y_tree import AccessibilityTreeParser, ActionableElement
from browserpilot.dom.spatial_matcher import ViewportBounds, is_element_visible


def test_actionable_element_prompt_line() -> None:
    """Verify that ActionableElement emits a compact, structured prompt representation."""
    elem = ActionableElement(
        id=14,
        role="button",
        name="Checkout",
        value=None,
        x=200.0,
        y=400.0,
        width=100.0,
        height=40.0,
        tag="button",
        is_focused=True,
    )
    assert elem.center_x == 250.0
    assert elem.center_y == 420.0

    prompt_line = elem.to_prompt_line()
    assert "[14] button \"Checkout\" (x:250, y:420) [focused]" == prompt_line


def test_accessibility_tree_formatting() -> None:
    """Verify format_prompt_tree produces multi-line compact prompts."""
    elements = [
        ActionableElement(
            id=1,
            role="link",
            name="Home",
            x=10.0,
            y=10.0,
            width=50.0,
            height=20.0,
            tag="a",
        ),
        ActionableElement(
            id=2,
            role="textbox",
            name="Search",
            value="query text",
            x=100.0,
            y=10.0,
            width=200.0,
            height=30.0,
            tag="input",
        ),
    ]

    formatted = AccessibilityTreeParser.format_prompt_tree(elements)
    assert '[1] link "Home"' in formatted
    assert '[2] textbox "Search"' in formatted
    assert 'val="query text"' in formatted


def test_spatial_matcher_bounds_visibility() -> None:
    """Test viewport intersection calculations."""
    # Fully inside viewport
    inside = ViewportBounds(x=100, y=100, width=50, height=20)
    assert is_element_visible(inside, 1280, 800) is True

    # Off-screen to the right
    offscreen_right = ViewportBounds(x=1400, y=100, width=50, height=20)
    assert is_element_visible(offscreen_right, 1280, 800) is False

    # Tiny / invisible
    too_small = ViewportBounds(x=10, y=10, width=1, height=1)
    assert is_element_visible(too_small, 1280, 800) is False
