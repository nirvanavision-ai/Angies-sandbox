"""Reddit provider via official API or RSS fallback."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from trendbot.models import Platform, TutorialResult
from trendbot.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

# Subreddits relevant to each niche
NICHE_SUBREDDITS: dict[str, list[str]] = {
    "ai": ["artificial", "MachineLearning", "ChatGPT", "LocalLLaMA"],
    "coding": ["learnprogramming", "webdev", "Python", "programming"],
    "personal_development": ["selfimprovement", "getdisciplined", "productivity"],
    "ai_filmmaking": ["aivideo", "StableDiffusion", "runwayml"],
    "graphic_design": ["graphic_design", "design", "AdobeIllustrator"],
    "finance": ["personalfinance", "investing", "financialindependence"],
    "image_to_video": ["aivideo", "StableDiffusion"],
    "ai_agents": ["LangChain", "LocalLLaMA", "ChatGPTCoding"],
    "ai_music": ["udio", "SunoAI", "AIMusic"],
}


class RedditProvider(BaseProvider):
    name = "reddit"

    def __init__(self) -> None:
        self._client_id = os.environ.get("REDDIT_CLIENT_ID", "")
        self._client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")

    def available(self) -> bool:
        return bool(self._client_id and self._client_secret)

    async def search(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        # If we have OAuth creds, use the API; otherwise fall back to RSS
        if self.available():
            return await self._search_api(query, limit=limit)
        return await self._search_rss(query, limit=limit)

    async def _search_api(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Get OAuth token
                auth_resp = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=(self._client_id, self._client_secret),
                    data={"grant_type": "client_credentials"},
                    headers={"User-Agent": "trendbot/0.1"},
                )
                auth_resp.raise_for_status()
                token = auth_resp.json()["access_token"]

                headers = {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "trendbot/0.1",
                }
                resp = await client.get(
                    "https://oauth.reddit.com/search",
                    params={
                        "q": f"{query} tutorial",
                        "sort": "hot",
                        "t": "month",
                        "limit": min(limit, 100),
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                return _parse_listing(resp.json())
        except httpx.HTTPError as exc:
            logger.warning("Reddit API error: %s — falling back to RSS", exc)
            return await self._search_rss(query, limit=limit)

    async def _search_rss(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        """Fallback: use Reddit's public JSON endpoint (no auth needed)."""
        results: list[TutorialResult] = []
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    f"https://www.reddit.com/search.json",
                    params={
                        "q": f"{query} tutorial",
                        "sort": "hot",
                        "t": "month",
                        "limit": min(limit, 25),
                    },
                    headers={"User-Agent": "trendbot/0.1"},
                )
                resp.raise_for_status()
                results = _parse_listing(resp.json())
        except httpx.HTTPError as exc:
            logger.warning("Reddit RSS fallback failed: %s", exc)
        return results


def _parse_listing(data: dict) -> list[TutorialResult]:
    results: list[TutorialResult] = []
    children = data.get("data", {}).get("children", [])
    for child in children:
        d = child.get("data", {})
        url = d.get("url", "")
        created = d.get("created_utc")
        results.append(
            TutorialResult(
                title=d.get("title", ""),
                url=url,
                platform=Platform.REDDIT,
                description=d.get("selftext", "")[:1000],
                publish_date=datetime.fromtimestamp(created, tz=timezone.utc) if created else None,
                view_count=d.get("score"),
                comment_count=d.get("num_comments"),
                provider_source="reddit",
                raw_metadata={
                    "subreddit": d.get("subreddit"),
                    "upvote_ratio": d.get("upvote_ratio"),
                    "source": "reddit",
                },
            )
        )
    return results
