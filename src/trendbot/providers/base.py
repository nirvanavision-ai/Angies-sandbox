"""Base class for all search / discovery providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from trendbot.models import TutorialResult


class ProviderError(Exception):
    """Non-fatal provider error (missing key, rate limit, etc.)."""


class BaseProvider(ABC):
    """All providers implement this interface."""

    name: str = "base"

    @abstractmethod
    async def search(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        """Run a search and return tutorial results."""
        ...

    def available(self) -> bool:
        """Return True if the provider has credentials / is configured."""
        return True
