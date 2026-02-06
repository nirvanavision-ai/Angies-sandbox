"""Creative concept / idea engine — generates WTF-but-wholesome content ideas."""

from __future__ import annotations

import logging

from trendbot.llm import LLMClient
from trendbot.models import ConceptIdea, TutorialResult

logger = logging.getLogger(__name__)

_SYSTEM = """You are a viral content strategist known for creating "WTF, that's genius!" reactions.
Your ideas must be:
- Wholesome and brand-safe (no profanity, no controversy)
- Surprisingly creative — the kind of thing nobody's done before
- Practically executable with AI music + short-form video
- Funny, memorable, and shareable

Respond ONLY with valid JSON: an array of 3-5 concept objects, each with:
{
  "hook": "The opening line/moment that grabs attention",
  "angle": "The creative angle/perspective",
  "comedic_twist": "What makes it funny or surprising",
  "format": "The content format (e.g., TikTok duet, YouTube Short, etc.)",
  "why_viral": "Why this would go viral"
}"""

_PROMPT = """Generate 3-5 creative, WTF-level content concepts for turning this tutorial into viral content.

Tutorial: {title}
Niche: {niche}
Description: {description}
Key topic: {topic}

The goal is to create content that makes people say "I can't believe someone made a SONG about this tutorial"
while still being educational and accurate. Think about:
- Unexpected musical genres for this topic
- Comedic visual concepts for the music video
- Surprising collaborations or mashup ideas
- Cultural references that make it relatable
- Meme-worthy moments people would screenshot/share

Respond with a JSON array of concept objects."""


async def generate_concepts(
    tutorial: TutorialResult,
    llm: LLMClient,
    *,
    topic: str = "",
) -> list[ConceptIdea]:
    """Generate 3-5 creative content concepts for a tutorial."""
    prompt = _PROMPT.format(
        title=tutorial.title,
        niche=tutorial.niche.value,
        description=tutorial.description[:500],
        topic=topic or tutorial.niche.value,
    )

    try:
        data = await llm.generate_json(prompt, system=_SYSTEM, max_tokens=2048)
        # Handle both array and dict-with-array responses
        items = data if isinstance(data, list) else data.get("concepts", data.get("ideas", []))
        if not isinstance(items, list):
            items = [items]

        return [
            ConceptIdea(
                hook=c.get("hook", ""),
                angle=c.get("angle", ""),
                comedic_twist=c.get("comedic_twist", ""),
                format=c.get("format", ""),
                why_viral=c.get("why_viral", ""),
            )
            for c in items[:5]
        ]
    except Exception as exc:
        logger.warning("Concept generation failed for %s: %s", tutorial.title, exc)
        return []
