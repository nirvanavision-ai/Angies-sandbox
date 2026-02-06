"""LLM self-critique: decide if a tutorial is a real trend vs noise."""

from __future__ import annotations

import json
import logging

from trendbot.llm import LLMClient
from trendbot.models import CritiqueResult, TrendType, TutorialResult

logger = logging.getLogger(__name__)

_SYSTEM = """You are a trend analyst. Given a tutorial's metadata, decide whether it represents
a genuine trending topic or is noise/evergreen/spam. Be strict — only confirm true trends.
Respond ONLY with valid JSON matching this schema exactly:
{
  "is_trend": bool,
  "confidence": float (0-1),
  "reasons": [string],
  "red_flags": [string],
  "what_to_verify": [string],
  "trend_type": "emerging" | "growing" | "peaking" | "sustained" | "fading"
}"""

_PROMPT_TEMPLATE = """Analyze this tutorial and determine if it represents a real, current trend.

Title: {title}
URL: {url}
Platform: {platform}
Niche: {niche}
Published: {publish_date}
Views: {views}
Likes: {likes}
Comments: {comments}
Description: {description}

Scoring info:
- Recency score: {recency}
- Engagement score: {engagement}
- Cross-platform mentions: {cross_platform}

Criteria for a real trend:
1. The topic is currently growing in interest (not just evergreen)
2. It has measurable engagement signals
3. Multiple sources discuss it
4. It's not spam, clickbait, or misleading
5. It's timely — relates to recent developments

Respond with strict JSON only."""


async def critique_tutorial(
    tutorial: TutorialResult,
    llm: LLMClient,
    *,
    recency_score: float = 0.0,
    engagement_score: float = 0.0,
    cross_platform: int = 1,
) -> CritiqueResult:
    """Use LLM to critique whether a tutorial is a genuine trend."""
    prompt = _PROMPT_TEMPLATE.format(
        title=tutorial.title,
        url=tutorial.url,
        platform=tutorial.platform.value,
        niche=tutorial.niche.value,
        publish_date=tutorial.publish_date.isoformat() if tutorial.publish_date else "unknown",
        views=tutorial.view_count or "unknown",
        likes=tutorial.like_count or "unknown",
        comments=tutorial.comment_count or "unknown",
        description=tutorial.description[:500],
        recency=recency_score,
        engagement=engagement_score,
        cross_platform=cross_platform,
    )

    try:
        data = await llm.generate_json(prompt, system=_SYSTEM, max_tokens=1024)
        trend_type_str = data.get("trend_type", "emerging")
        try:
            trend_type = TrendType(trend_type_str)
        except ValueError:
            trend_type = TrendType.EMERGING

        return CritiqueResult(
            is_trend=data.get("is_trend", False),
            confidence=float(data.get("confidence", 0.0)),
            reasons=data.get("reasons", []),
            red_flags=data.get("red_flags", []),
            what_to_verify=data.get("what_to_verify", []),
            trend_type=trend_type,
        )
    except Exception as exc:
        logger.warning("Critique failed for %s: %s", tutorial.title, exc)
        return CritiqueResult(
            is_trend=False,
            confidence=0.0,
            reasons=["Critique failed"],
            red_flags=[str(exc)],
        )
