"""YouTube Data API v3 provider."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from trendbot.models import Platform, TutorialResult
from trendbot.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)


class YouTubeProvider(BaseProvider):
    name = "youtube"

    def __init__(self) -> None:
        self._api_key = os.environ.get("YOUTUBE_API_KEY", "")
        self._base = "https://www.googleapis.com/youtube/v3"

    def available(self) -> bool:
        return bool(self._api_key)

    async def search(self, query: str, *, limit: int = 20) -> list[TutorialResult]:
        if not self.available():
            logger.warning("YouTube API key not set — skipping")
            return []

        results: list[TutorialResult] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Step 1: search
                search_resp = await client.get(
                    f"{self._base}/search",
                    params={
                        "key": self._api_key,
                        "q": f"{query} tutorial",
                        "part": "snippet",
                        "type": "video",
                        "order": "viewCount",
                        "maxResults": min(limit, 50),
                        "publishedAfter": _recent_iso(),
                    },
                )
                search_resp.raise_for_status()
                items = search_resp.json().get("items", [])

                if not items:
                    return []

                # Step 2: get statistics for all videos in one call
                video_ids = [
                    it["id"]["videoId"]
                    for it in items
                    if it.get("id", {}).get("videoId")
                ]
                stats = await self._fetch_stats(client, video_ids)

                for item in items:
                    vid = item.get("id", {}).get("videoId", "")
                    if not vid:
                        continue
                    snippet = item.get("snippet", {})
                    st = stats.get(vid, {})
                    pub = snippet.get("publishedAt")
                    results.append(
                        TutorialResult(
                            title=snippet.get("title", ""),
                            url=f"https://www.youtube.com/watch?v={vid}",
                            platform=Platform.YOUTUBE,
                            description=snippet.get("description", "")[:1000],
                            publish_date=datetime.fromisoformat(pub.replace("Z", "+00:00")) if pub else None,
                            view_count=_int_or_none(st.get("viewCount")),
                            like_count=_int_or_none(st.get("likeCount")),
                            comment_count=_int_or_none(st.get("commentCount")),
                            provider_source="youtube",
                            raw_metadata={
                                "video_id": vid,
                                "channel": snippet.get("channelTitle", ""),
                                "source": "youtube",
                            },
                        )
                    )
        except httpx.HTTPError as exc:
            raise ProviderError(f"YouTube API error: {exc}") from exc
        return results

    async def _fetch_stats(self, client: httpx.AsyncClient, ids: list[str]) -> dict[str, dict]:
        if not ids:
            return {}
        resp = await client.get(
            f"{self._base}/videos",
            params={
                "key": self._api_key,
                "id": ",".join(ids[:50]),
                "part": "statistics",
            },
        )
        resp.raise_for_status()
        return {
            it["id"]: it.get("statistics", {})
            for it in resp.json().get("items", [])
        }

    async def fetch_transcript(self, video_id: str) -> str:
        """Attempt to fetch transcript via youtube-transcript-api (optional dep)."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            entries = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join(e["text"] for e in entries)
        except Exception:
            logger.debug("Transcript fetch failed for %s — falling back to description", video_id)
            return ""


def _recent_iso() -> str:
    """ISO timestamp for 30 days ago."""
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(days=30)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _int_or_none(v: str | None) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None
