"""Unified multi-provider LLM interface supporting OpenAI, Anthropic Claude, Gemini, and Ollama."""

import json
import logging
import os
import re
import time
from typing import Any
from pydantic import BaseModel, Field
from browserpilot.config import Settings, get_settings

logger = logging.getLogger("browserpilot.agent.models")

# Cost per 1M tokens in USD: (input_cost_per_m, output_cost_per_m)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
}


class LLMResponse(BaseModel):
    """Structured LLM completion payload with token and cost metadata."""

    content: str
    parsed_json: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float


def compute_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate monetary expense for a model inference call."""
    # Find matching pricing checking most specific model names first
    pricing = None
    lower_model = model_name.lower()

    # Exact match first
    if lower_model in MODEL_PRICING:
        pricing = MODEL_PRICING[lower_model]
    else:
        # Longest matching key first
        for key in sorted(MODEL_PRICING.keys(), key=len, reverse=True):
            if key in lower_model:
                pricing = MODEL_PRICING[key]
                break

    if not pricing:
        pricing = (1.00, 3.00)  # Conservative generic rate

    in_rate, out_rate = pricing
    cost = (prompt_tokens * (in_rate / 1_000_000.0)) + (
        completion_tokens * (out_rate / 1_000_000.0)
    )
    return round(cost, 6)


def extract_json_from_text(text: str) -> dict[str, Any]:
    """Parse JSON payload from model output, stripping markdown fences or preamble."""
    trimmed = text.strip()

    # Match markdown code block ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", trimmed)
    if match:
        trimmed = match.group(1).strip()

    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        # Fallback: attempt to find outermost curly braces
        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start != -1 and end != -1 and end > start:
            sub = trimmed[start : end + 1]
            return json.loads(sub)
        raise ValueError(f"Failed to extract valid JSON from LLM response: {text[:200]}")


class LLMClient:
    """Dispatches reasoning requests across configured provider APIs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def generate_action(
        self,
        system_prompt: str,
        user_prompt: str,
        override_model: str | None = None,
    ) -> LLMResponse:
        """Execute a completion request and parse the structured action response."""
        start_time = time.perf_counter()
        provider = self.settings.llm_provider
        model = override_model or self.settings.llm_model

        if provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_prompt, model, start_time)
        elif provider in ("openai", "gemini", "ollama"):
            return await self._call_openai_compatible(
                system_prompt, user_prompt, model, start_time, provider
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def _call_openai_compatible(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        start_time: float,
        provider: str,
    ) -> LLMResponse:
        """Call OpenAI, Gemini, or Ollama using the standard OpenAI client protocol."""
        from openai import AsyncOpenAI

        api_key = self.settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        base_url = self.settings.llm_base_url

        if provider == "gemini":
            api_key = (
                self.settings.gemini_api_key
                or os.getenv("GEMINI_API_KEY")
                or api_key
            )
            base_url = (
                base_url
                or "https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        elif provider == "ollama":
            base_url = base_url or "http://localhost:11434/v1"
            api_key = api_key or "ollama"

        if not api_key and provider != "ollama":
            raise ValueError(
                f"Missing API key for provider '{provider}'. "
                f"Please set {provider.upper()}_API_KEY in your environment or .env file."
            )

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        response = await client.chat.completions.create(
            model=model,
            temperature=self.settings.temperature,
            response_format={"type": "json_object"} if "gpt" in model else None,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_content = response.choices[0].message.content or "{}"
        parsed = extract_json_from_text(raw_content)

        prompt_tokens = (
            response.usage.prompt_tokens if response.usage else len(user_prompt) // 4
        )
        completion_tokens = (
            response.usage.completion_tokens
            if response.usage
            else len(raw_content) // 4
        )
        total_tokens = prompt_tokens + completion_tokens

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        cost = compute_cost(model, prompt_tokens, completion_tokens)

        return LLMResponse(
            content=raw_content,
            parsed_json=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=round(latency_ms, 2),
        )

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        start_time: float,
    ) -> LLMResponse:
        """Call Anthropic Messages API."""
        from anthropic import AsyncAnthropic

        api_key = self.settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "Missing API key for Anthropic. Please set ANTHROPIC_API_KEY in your environment or .env file."
            )
        client = AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=self.settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_content = ""
        for block in response.content:
            if getattr(block, "type", "") == "text":
                raw_content += block.text

        parsed = extract_json_from_text(raw_content)
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        total_tokens = prompt_tokens + completion_tokens

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        cost = compute_cost(model, prompt_tokens, completion_tokens)

        return LLMResponse(
            content=raw_content,
            parsed_json=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=round(latency_ms, 2),
        )
