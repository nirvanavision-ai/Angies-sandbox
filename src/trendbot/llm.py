"""LLM client abstraction — swap between OpenAI and Anthropic."""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Provider-agnostic LLM interface."""

    @abstractmethod
    async def generate_text(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> str:
        ...

    @abstractmethod
    async def generate_json(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> dict[str, Any]:
        ...


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of JSON from LLM output."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try finding first { ... } block
    depth = 0
    start = None
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = None
    raise ValueError(f"Could not extract JSON from LLM output: {text[:200]!r}")


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model

    async def generate_text(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        resp = await self._client.messages.create(**kwargs)
        return resp.content[0].text

    async def generate_json(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> dict[str, Any]:
        text = await self.generate_text(prompt, system=system, max_tokens=max_tokens)
        return _extract_json(text)


class OpenAIClient(LLMClient):
    """OpenAI GPT client."""

    def __init__(self, model: str = "gpt-4o") -> None:
        import openai
        self._client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self._model = model

    async def generate_text(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await self._client.chat.completions.create(
            model=self._model, messages=messages, max_tokens=max_tokens
        )
        return resp.choices[0].message.content or ""

    async def generate_json(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> dict[str, Any]:
        text = await self.generate_text(prompt, system=system, max_tokens=max_tokens)
        return _extract_json(text)


class MockLLMClient(LLMClient):
    """Deterministic mock for testing / offline demo."""

    async def generate_text(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> str:
        return "[MockLLM] Response to: " + prompt[:80]

    async def generate_json(self, prompt: str, *, system: str = "", max_tokens: int = 4096) -> dict[str, Any]:
        return {"mock": True, "prompt_preview": prompt[:80]}


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Factory: pick the right LLM client based on env / explicit choice."""
    provider = provider or os.environ.get("TRENDBOT_LLM_PROVIDER", "anthropic")
    provider = provider.lower()
    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    if provider == "openai" and os.environ.get("OPENAI_API_KEY"):
        return OpenAIClient()
    # Fall back to whichever key is available
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIClient()
    logger.warning("No LLM API key found — using MockLLMClient")
    return MockLLMClient()
