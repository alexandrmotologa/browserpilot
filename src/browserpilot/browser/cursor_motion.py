"""Human-like cursor trajectory emulator using cubic Bezier curves and micro-jitter."""

import asyncio
import math
import random
from typing import Any


class CursorMotion:
    """Simulates authentic human mouse trajectories across the browser viewport."""

    def __init__(self, start_x: float = 100.0, start_y: float = 100.0) -> None:
        self.x = start_x
        self.y = start_y

    @staticmethod
    def _bezier_point(
        p0: float, p1: float, p2: float, p3: float, t: float
    ) -> float:
        """Evaluate a cubic Bezier curve at interpolation parameter t (0 <= t <= 1)."""
        return (
            ((1 - t) ** 3) * p0
            + 3 * ((1 - t) ** 2) * t * p1
            + 3 * (1 - t) * (t**2) * p2
            + (t**3) * p3
        )

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Apply smooth ease-in-out interpolation curve."""
        return t * t * (3.0 - 2.0 * t)

    def generate_path(
        self, target_x: float, target_y: float, steps: int | None = None
    ) -> list[tuple[float, float]]:
        """Compute human-like waypoint coordinates between current position and target."""
        p0_x, p0_y = self.x, self.y
        p3_x, p3_y = target_x, target_y

        dist = math.hypot(p3_x - p0_x, p3_y - p0_y)
        if steps is None:
            # Scale step count dynamically based on travel distance
            steps = max(12, min(40, int(dist / 25.0)))

        # Calculate perpendicular angle for natural arc deviation
        dx = p3_x - p0_x
        dy = p3_y - p0_y
        angle = math.atan2(dy, dx)
        perp_angle = angle + (math.pi / 2 if random.random() > 0.5 else -math.pi / 2)

        # Deviation magnitude relative to distance
        deviation = min(dist * 0.3, random.uniform(20.0, 80.0))

        # Two internal control points with randomized lateral offsets
        p1_x = p0_x + (dx * 0.3) + math.cos(perp_angle) * (deviation * random.uniform(0.6, 1.2))
        p1_y = p0_y + (dy * 0.3) + math.sin(perp_angle) * (deviation * random.uniform(0.6, 1.2))

        p2_x = p0_x + (dx * 0.7) + math.cos(perp_angle) * (deviation * random.uniform(0.2, 0.7))
        p2_y = p0_y + (dy * 0.7) + math.sin(perp_angle) * (deviation * random.uniform(0.2, 0.7))

        points: list[tuple[float, float]] = []
        for i in range(1, steps + 1):
            raw_t = i / steps
            eased_t = self._ease_in_out(raw_t)

            x = self._bezier_point(p0_x, p1_x, p2_x, p3_x, eased_t)
            y = self._bezier_point(p0_y, p1_y, p2_y, p3_y, eased_t)

            # Add minor micro-jitter except near the end of the path
            if i < steps - 2:
                x += random.gauss(0, 0.8)
                y += random.gauss(0, 0.8)

            points.append((x, y))

        return points

    async def move_to(
        self, page: Any, target_x: float, target_y: float
    ) -> None:
        """Smoothly move mouse pointer to destination coordinates on the given page."""
        path = self.generate_path(target_x, target_y)

        for px, py in path:
            await page.mouse.move(px, py)
            self.x, self.y = px, py
            # Sleep variable interval between 4ms and 14ms for organic velocity
            await asyncio.sleep(random.uniform(0.004, 0.014))

        # Snap to exact destination at finish
        await page.mouse.move(target_x, target_y)
        self.x, self.y = target_x, target_y

    async def click_at(
        self,
        page: Any,
        target_x: float,
        target_y: float,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        """Traverse to coordinates with natural motion, pause, and dispatch mouse click."""
        await self.move_to(page, target_x, target_y)
        # Authentic pre-click hesitation
        await asyncio.sleep(random.uniform(0.06, 0.18))
        await page.mouse.click(target_x, target_y, button=button, click_count=click_count)
        # Authentic post-click dwell
        await asyncio.sleep(random.uniform(0.05, 0.12))
