"""Tavily search provider for web discovery."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from trendbot.models import Platform, TutorialResult
from trendbot.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)


class TavilyProvider(BaseProvider):
    name = "tavily"

    def __init__(self) -> None:
        self._api_key = os.environ.get("TAVILY_API_KEY", "")
        self._base_url = "https://api.tavily.com"

    def available(self) -> bool:
        return bool(self._api_key)

    async def search(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        if not self.available():
            logger.warning("Tavily API key not set — skipping")
            return []

        search_query = f"{query} tutorial"
        payload = {
            "api_key": self._api_key,
            "query": search_query,
            "search_depth": "advanced",
            "max_results": min(limit, 20),  # Tavily max per request
            "include_answer": False,
            "include_raw_content": False,
        }

        results: list[TutorialResult] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self._base_url}/search", json=payload)
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("results", []):
                url = item.get("url", "")
                platform = _guess_platform(url)
                results.append(
                    TutorialResult(
                        title=item.get("title", ""),
                        url=url,
                        platform=platform,
                        description=item.get("content", "")[:1000],
                        provider_source="tavily",
                        raw_metadata={"score": item.get("score"), "source": "tavily"},
                    )
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Tavily request failed: {exc}") from exc

        return results


def _guess_platform(url: str) -> Platform:
    host = (httpx.URL(url).host or "").lower()
    if "youtube.com" in host or "youtu.be" in host:
        return Platform.YOUTUBE
    if "medium.com" in host:
        return Platform.MEDIUM
    if "substack.com" in host:
        return Platform.SUBSTACK
    if "github.com" in host:
        return Platform.GITHUB
    if "reddit.com" in host:
        return Platform.REDDIT
    if "dev.to" in host:
        return Platform.DEV_TO
    return Platform.WEB
