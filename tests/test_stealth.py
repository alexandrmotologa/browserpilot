"""Tests for stealth evasion scripts and fingerprint overrides."""

from browserpilot.browser.fingerprint import get_stealth_scripts


def test_stealth_scripts_contain_key_evasions() -> None:
    """Verify presence of key browser fingerprint override routines."""
    scripts = get_stealth_scripts()
    assert len(scripts) >= 1

    combined = "\n".join(scripts)
    assert "navigator" in combined
    assert "webdriver" in combined
    assert "chrome.runtime" in combined
    assert "plugins" in combined
    assert "UNMASKED_VENDOR_WEBGL" in combined
    assert "UNMASKED_RENDERER_WEBGL" in combined
