"""Browser and stealth execution subsystem."""

from browserpilot.browser.cursor_motion import CursorMotion
from browserpilot.browser.fingerprint import get_stealth_scripts
from browserpilot.browser.stealth_context import BrowserManager

__all__ = ["BrowserManager", "CursorMotion", "get_stealth_scripts"]
