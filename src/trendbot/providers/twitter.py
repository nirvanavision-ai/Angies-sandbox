"""Twitter/X provider stub — requires API key (not available by default)."""

from __future__ import annotations

import logging

from trendbot.models import TutorialResult
from trendbot.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class TwitterProvider(BaseProvider):
    """Stub provider for X/Twitter. Implement when API access is available."""

    name = "twitter"

    def available(self) -> bool:
        return False  # No free API tier currently

    async def search(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        logger.info("Twitter provider is a stub — skipping")
        return []
