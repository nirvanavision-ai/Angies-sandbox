"""SerpAPI provider for Google search results."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from trendbot.models import Platform, TutorialResult
from trendbot.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)


class SerpAPIProvider(BaseProvider):
    name = "serpapi"

    def __init__(self) -> None:
        self._api_key = os.environ.get("SERPAPI_API_KEY", "")
        self._base_url = "https://serpapi.com/search.json"

    def available(self) -> bool:
        return bool(self._api_key)

    async def search(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        if not self.available():
            logger.warning("SerpAPI key not set — skipping")
            return []

        params = {
            "api_key": self._api_key,
            "q": f"{query} tutorial",
            "num": min(limit, 100),
            "engine": "google",
            "tbs": "qdr:m",  # past month
        }

        results: list[TutorialResult] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(self._base_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("organic_results", []):
                url = item.get("link", "")
                platform = _guess_platform(url)
                results.append(
                    TutorialResult(
                        title=item.get("title", ""),
                        url=url,
                        platform=platform,
                        description=item.get("snippet", ""),
                        provider_source="serpapi",
                        raw_metadata={
                            "position": item.get("position"),
                            "source": "serpapi",
                        },
                    )
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"SerpAPI request failed: {exc}") from exc

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
    return Platform.WEB
