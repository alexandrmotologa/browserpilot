"""Tests for CLI entrypoint and version flags."""

from typer.testing import CliRunner

from browserpilot import __version__
from browserpilot.cli import app

runner = CliRunner()


def test_cli_version_flag() -> None:
    """Verify --version and -v print version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"BrowserPilot v{__version__}" in result.stdout

    result_short = runner.invoke(app, ["-v"])
    assert result_short.exit_code == 0
    assert f"BrowserPilot v{__version__}" in result_short.stdout


def test_cli_version_command() -> None:
    """Verify version subcommand prints version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"BrowserPilot v{__version__}" in result.stdout
