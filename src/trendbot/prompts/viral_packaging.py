"""Viral packaging generator — titles, hooks, captions, hashtags."""

from __future__ import annotations

import logging

from trendbot.llm import LLMClient
from trendbot.models import TutorialResult, ViralPackaging

logger = logging.getLogger(__name__)

_SYSTEM = """You are a viral content packaging expert. You create irresistible titles, hooks, and
captions that maximize clicks and shares while remaining honest and not clickbait.

Respond ONLY with valid JSON:
{
  "suggested_title": "An irresistible but honest title",
  "ten_second_hook_script": "Spoken script for the first 10 seconds",
  "thumbnail_text_ideas": ["TEXT 1", "TEXT 2", "TEXT 3"],
  "tiktok_caption": "Caption for TikTok/Shorts (with emojis)",
  "hashtags": ["#hashtag1", "#hashtag2", ...]
}"""

_PROMPT = """Create viral packaging for this tutorial-turned-song:

Tutorial: {title}
Niche: {niche}
Why it's trending: {why_trending}
Song genre: {genre}

Create:
1. TITLE: Something that makes people think "I NEED to hear this" — combine the tutorial topic
   with the unexpected musical format. Keep under 80 characters.
2. 10-SECOND HOOK SCRIPT: The spoken words for the first 10 seconds of the video that
   stop people from scrolling. Must create curiosity or surprise.
3. THUMBNAIL TEXT: 3 options for bold text overlay on thumbnail (3-6 words each).
4. TIKTOK CAPTION: Short, punchy caption with emojis for TikTok/YouTube Shorts.
5. HASHTAGS: 10-15 relevant hashtags mixing niche + music + viral tags.

Respond with JSON only."""


async def generate_viral_packaging(
    tutorial: TutorialResult,
    llm: LLMClient,
    *,
    why_trending: str = "",
    genre: str = "",
) -> ViralPackaging:
    """Generate viral packaging for a tutorial song."""
    prompt = _PROMPT.format(
        title=tutorial.title,
        niche=tutorial.niche.value,
        why_trending=why_trending or "Currently trending in its niche",
        genre=genre or "pop",
    )

    try:
        data = await llm.generate_json(prompt, system=_SYSTEM, max_tokens=1024)
        return ViralPackaging(
            suggested_title=data.get("suggested_title", ""),
            ten_second_hook_script=data.get("ten_second_hook_script", ""),
            thumbnail_text_ideas=data.get("thumbnail_text_ideas", []),
            tiktok_caption=data.get("tiktok_caption", ""),
            hashtags=data.get("hashtags", []),
        )
    except Exception as exc:
        logger.warning("Viral packaging failed: %s", exc)
        return ViralPackaging()
