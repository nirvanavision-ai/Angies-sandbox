"""Tutorial → Song lyricist — converts tutorial content into catchy song lyrics."""

from __future__ import annotations

import logging

from trendbot.llm import LLMClient
from trendbot.models import LyricDraft, MusicSpec, TutorialResult

logger = logging.getLogger(__name__)

_SYSTEM = """You are a genius songwriter who specializes in educational music — think Schoolhouse Rock
meets modern pop. You create lyrics that are:
- Accurate to the tutorial content (no hallucinated steps)
- Catchy and memeable
- Fun to sing along to
- Structured with clear verse/chorus/bridge sections

Respond ONLY with valid JSON matching this schema:
{
  "verses": ["verse 1 text", "verse 2 text"],
  "chorus": "chorus text (encodes 3-5 key learning points)",
  "bridge": "bridge text",
  "rap_breakdown": "optional rap section with step-by-step breakdown",
  "step_callouts": ["Step 1: ...", "Step 2: ...", ...],
  "full_text": "complete lyrics with section labels"
}"""

_LYRICS_PROMPT = """Write song lyrics that teach this tutorial's content in a fun, memorable way.

Tutorial: {title}
Description: {description}
Transcript/Content: {content}
Requested style: {style}

Requirements:
1. The CHORUS must encode the 3-5 most important takeaways — it should be so catchy
   that someone who just hears the chorus learns the key points.
2. Each VERSE should cover a major section/concept from the tutorial.
3. Include a "STEP CALLOUT" section where steps are delivered as rhythmic spoken-word
   bullets (like "Step 1: Open your terminal / Step 2: Type pip install / ...").
4. Optional RAP BREAKDOWN for the most technical section.
5. Keep it clean, fun, and accurate — no hallucinated steps or information.
6. Use rhyme schemes that aid memorization.
7. Include [Section Labels] in the full_text.

Respond with JSON only."""


_MUSIC_SYSTEM = """You are a music producer who specializes in matching educational content
to the perfect musical vibe. Respond ONLY with valid JSON:
{
  "genre": "primary genre",
  "bpm_range": "120-130",
  "instruments": ["instrument1", "instrument2"],
  "vocal_style": "description of vocal approach",
  "vocal_references": ["Artist1", "Artist2"],
  "mood": "overall mood description"
}"""

_MUSIC_PROMPT = """Recommend the perfect music specification for a song-tutorial about:

Tutorial: {title}
Niche: {niche}
Requested style: {style}
Tone: Educational but fun and viral-worthy

Consider:
- What genre would make this topic SURPRISING and shareable?
- What BPM creates the right energy for learning?
- What instruments complement the subject matter?
- What vocal style would make this both entertaining and clear?

Respond with JSON only."""


async def write_lyrics(
    tutorial: TutorialResult,
    llm: LLMClient,
    *,
    style: str = "pop",
) -> LyricDraft:
    """Generate song lyrics from tutorial content."""
    content = tutorial.transcript or tutorial.description
    if not content:
        content = tutorial.title

    prompt = _LYRICS_PROMPT.format(
        title=tutorial.title,
        description=tutorial.description[:500],
        content=content[:3000],
        style=style,
    )

    try:
        data = await llm.generate_json(prompt, system=_SYSTEM, max_tokens=4096)
        return LyricDraft(
            verses=data.get("verses", []),
            chorus=data.get("chorus", ""),
            bridge=data.get("bridge", ""),
            rap_breakdown=data.get("rap_breakdown", ""),
            step_callouts=data.get("step_callouts", []),
            full_text=data.get("full_text", ""),
        )
    except Exception as exc:
        logger.warning("Lyric generation failed for %s: %s", tutorial.title, exc)
        return LyricDraft()


async def design_music_spec(
    tutorial: TutorialResult,
    llm: LLMClient,
    *,
    style: str = "",
) -> MusicSpec:
    """Generate a music specification for the tutorial song."""
    prompt = _MUSIC_PROMPT.format(
        title=tutorial.title,
        niche=tutorial.niche.value,
        style=style or "auto-detect best genre",
    )

    try:
        data = await llm.generate_json(prompt, system=_MUSIC_SYSTEM, max_tokens=1024)
        return MusicSpec(
            genre=data.get("genre", ""),
            bpm_range=data.get("bpm_range", ""),
            instruments=data.get("instruments", []),
            vocal_style=data.get("vocal_style", ""),
            vocal_references=data.get("vocal_references", []),
            mood=data.get("mood", ""),
        )
    except Exception as exc:
        logger.warning("Music spec failed for %s: %s", tutorial.title, exc)
        return MusicSpec()
