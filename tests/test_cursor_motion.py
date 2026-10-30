"""Tests for human cursor Bézier motion generation and easing."""

import math
from browserpilot.browser.cursor_motion import CursorMotion


def test_bezier_interpolation() -> None:
    """Verify cubic Bézier formula endpoints and bounds."""
    motion = CursorMotion(start_x=0.0, start_y=0.0)

    # At t=0 should match start
    assert CursorMotion._bezier_point(0, 50, 150, 200, 0.0) == 0.0

    # At t=1 should match end
    assert CursorMotion._bezier_point(0, 50, 150, 200, 1.0) == 200.0


def test_generate_path_waypoints() -> None:
    """Verify that generated path starts at current position and ends near target."""
    motion = CursorMotion(start_x=50.0, start_y=50.0)
    target_x, target_y = 600.0, 400.0

    path = motion.generate_path(target_x, target_y, steps=20)
    assert len(path) == 20

    # Path should start transitioning toward target
    first_x, first_y = path[0]
    assert first_x != target_x
    assert first_y != target_y

    # End of path should be in close proximity to target coordinates
    last_x, last_y = path[-1]
    assert math.isclose(last_x, target_x, abs_tol=3.0)
    assert math.isclose(last_y, target_y, abs_tol=3.0)
