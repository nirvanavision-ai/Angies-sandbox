"""Provider registry — discover and run all configured providers."""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from trendbot.models import TutorialResult
from trendbot.providers.base import BaseProvider, ProviderError
from trendbot.providers.github import GitHubProvider
from trendbot.providers.reddit import RedditProvider
from trendbot.providers.serpapi import SerpAPIProvider
from trendbot.providers.tavily import TavilyProvider
from trendbot.providers.twitter import TwitterProvider
from trendbot.providers.youtube import YouTubeProvider

logger = logging.getLogger(__name__)


ALL_PROVIDERS: list[type[BaseProvider]] = [
    TavilyProvider,
    SerpAPIProvider,
    YouTubeProvider,
    RedditProvider,
    GitHubProvider,
    TwitterProvider,
]


def get_available_providers() -> list[BaseProvider]:
    """Instantiate all providers that have valid credentials."""
    providers: list[BaseProvider] = []
    for cls in ALL_PROVIDERS:
        p = cls()
        if p.available():
            providers.append(p)
            logger.info("Provider available: %s", p.name)
        else:
            logger.debug("Provider unavailable: %s", p.name)
    return providers


async def run_all_providers(
    query: str,
    *,
    providers: Sequence[BaseProvider] | None = None,
    limit: int = 20,
) -> list[TutorialResult]:
    """Fan out searches across all available providers concurrently."""
    if providers is None:
        providers = get_available_providers()

    if not providers:
        logger.warning("No providers available — returning empty results")
        return []

    async def _run(p: BaseProvider) -> list[TutorialResult]:
        try:
            return await p.search(query, limit=limit)
        except ProviderError as exc:
            logger.warning("Provider %s failed: %s", p.name, exc)
            return []

    tasks = [_run(p) for p in providers]
    all_results = await asyncio.gather(*tasks)
    # Flatten
    flat: list[TutorialResult] = []
    for batch in all_results:
        flat.extend(batch)
    return flat
