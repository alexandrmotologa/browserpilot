"""Configuration and environment management for BrowserPilot."""

from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings for the BrowserPilot agent and server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Provider Configuration
    llm_provider: Literal["openai", "anthropic", "gemini", "ollama"] = Field(
        default="openai",
        description="Active LLM provider backend",
    )
    llm_model: str = Field(
        default="gpt-4o",
        description="Target model identifier",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API authentication key",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic Claude API key",
    )
    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="Optional custom API base URL for Ollama or OpenAI-compatible proxies",
    )
    temperature: float = Field(
        default=0.1,
        description="Sampling temperature for action reasoning",
    )

    # Browser & Stealth Configuration
    headless: bool = Field(
        default=False,
        description="Run browser in headless mode",
    )
    use_stealth: bool = Field(
        default=True,
        description="Enable stealth evasions and fingerprint normalization",
    )
    prefer_patchright: bool = Field(
        default=True,
        description="Prefer patchright binary over standard playwright if installed",
    )
    viewport_width: int = Field(default=1280, description="Browser viewport width")
    viewport_height: int = Field(default=800, description="Browser viewport height")
    browser_timeout_ms: int = Field(
        default=30000,
        description="Default navigation and locator timeout in milliseconds",
    )
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        description="Default browser User-Agent string",
    )

    # Agent Planning & Execution Limits
    max_steps: int = Field(
        default=30,
        description="Maximum execution steps before aborting a mission",
    )
    max_retries_per_action: int = Field(
        default=3,
        description="Retry attempts on failing actions before replanning",
    )
    enable_human_takeover: bool = Field(
        default=True,
        description="Automatically pause execution when CAPTCHA or 2FA is detected",
    )

    # Server Configuration
    host: str = Field(default="127.0.0.1", description="FastAPI host address")
    port: int = Field(default=9660, description="FastAPI and Web Studio port")


@lru_cache
def get_settings() -> Settings:
    """Return cached instance of application settings."""
    return Settings()
