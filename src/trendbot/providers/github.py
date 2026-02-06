"""GitHub trending / search provider."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

from trendbot.models import Platform, TutorialResult
from trendbot.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)


class GitHubProvider(BaseProvider):
    name = "github"

    def __init__(self) -> None:
        self._token = os.environ.get("GITHUB_TOKEN", "")

    def available(self) -> bool:
        # GitHub search API works without a token, but has tighter rate limits
        return True

    async def search(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        results: list[TutorialResult] = []
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        search_q = f"{query} tutorial in:name,description,readme created:>{since}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": search_q,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": min(limit, 30),
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("items", []):
                created = item.get("created_at")
                results.append(
                    TutorialResult(
                        title=item.get("full_name", ""),
                        url=item.get("html_url", ""),
                        platform=Platform.GITHUB,
                        description=item.get("description", "") or "",
                        publish_date=(
                            datetime.fromisoformat(created.replace("Z", "+00:00"))
                            if created
                            else None
                        ),
                        view_count=item.get("stargazers_count"),
                        provider_source="github",
                        raw_metadata={
                            "stars": item.get("stargazers_count"),
                            "forks": item.get("forks_count"),
                            "language": item.get("language"),
                            "source": "github",
                        },
                    )
                )
        except httpx.HTTPError as exc:
            logger.warning("GitHub API error: %s", exc)

        return results
