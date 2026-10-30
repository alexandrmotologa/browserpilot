"""Spatial coordinate calculation, viewport intersection, and element visibility checking."""

from pydantic import BaseModel


class ViewportBounds(BaseModel):
    """Represents a rectangular bounding box in viewport space."""

    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        """Horizontal midpoint coordinate."""
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        """Vertical midpoint coordinate."""
        return self.y + (self.height / 2.0)

    def intersects(self, viewport_width: float, viewport_height: float) -> bool:
        """Check if any portion of the rectangle lies within the visible viewport."""
        if self.width <= 0 or self.height <= 0:
            return False
        if self.x + self.width < 0 or self.x > viewport_width:
            return False
        if self.y + self.height < 0 or self.y > viewport_height:
            return False
        return True


def is_element_visible(
    bounds: ViewportBounds,
    viewport_width: float,
    viewport_height: float,
    min_dimension: float = 4.0,
) -> bool:
    """Determine whether an element is large enough and within view to be actionable."""
    if bounds.width < min_dimension or bounds.height < min_dimension:
        return False
    return bounds.intersects(viewport_width, viewport_height)
