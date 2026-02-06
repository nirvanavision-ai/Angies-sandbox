"""Suno (and Udio) prompt generation from lyrics + music spec."""

from __future__ import annotations

import logging

from trendbot.llm import LLMClient
from trendbot.models import LyricDraft, MusicSpec, SunoPrompt, TutorialResult

logger = logging.getLogger(__name__)

_SYSTEM = """You are an expert at crafting prompts for AI music generation platforms (Suno, Udio).
You understand what makes Suno produce great results:
- Clear genre/style tags
- Specific vocal direction
- Mood and energy descriptors
- Clean, well-structured lyrics with section markers

Respond ONLY with valid JSON:
{
  "title": "Song title",
  "style_prompt": "Suno style/genre prompt (no lyrics here)",
  "lyrics": "Full lyrics with [Verse], [Chorus], [Bridge] markers for Suno",
  "negative_prompt": "What to avoid (optional)",
  "short_version_lyrics": "45-second hook version lyrics",
  "full_version_lyrics": "Full 2-3 minute version lyrics"
}"""

_PROMPT = """Create optimized Suno AI music generation prompts for this tutorial song.

Tutorial: {title}
Music Spec:
- Genre: {genre}
- BPM: {bpm}
- Instruments: {instruments}
- Vocal Style: {vocal_style}
- Mood: {mood}

Lyrics Draft:
{lyrics}

Platform: {platform}

Requirements:
1. STYLE PROMPT: Write a concise style description for Suno (genre, energy, instruments, vocal style).
   Example: "Upbeat indie pop, male vocals, acoustic guitar, handclaps, 120 BPM, educational, fun"
2. LYRICS: Format the lyrics with Suno-compatible section markers: [Intro], [Verse 1], [Chorus], etc.
3. SHORT VERSION: Create a 45-second hook version (just the catchiest chorus + one verse).
4. FULL VERSION: Complete 2-3 minute song with all sections.
5. NEGATIVE PROMPT: Specify what to avoid (e.g., "avoid mumbling, avoid off-key vocals,
   avoid distortion, avoid explicit content").

Make the style prompt punchy and specific — Suno works best with clear genre + mood + instrumentation tags.

Respond with JSON only."""


async def generate_suno_prompt(
    tutorial: TutorialResult,
    lyrics: LyricDraft,
    music_spec: MusicSpec,
    llm: LLMClient,
    *,
    platform: str = "suno",
) -> SunoPrompt:
    """Generate platform-specific prompts for Suno or Udio."""
    instruments_str = ", ".join(music_spec.instruments) if music_spec.instruments else "auto"

    prompt = _PROMPT.format(
        title=tutorial.title,
        genre=music_spec.genre or "auto-detect",
        bpm=music_spec.bpm_range or "auto",
        instruments=instruments_str,
        vocal_style=music_spec.vocal_style or "auto",
        mood=music_spec.mood or "fun and educational",
        lyrics=lyrics.full_text or lyrics.chorus or "No lyrics provided",
        platform=platform,
    )

    try:
        data = await llm.generate_json(prompt, system=_SYSTEM, max_tokens=4096)
        return SunoPrompt(
            title=data.get("title", tutorial.title),
            style_prompt=data.get("style_prompt", ""),
            lyrics=data.get("lyrics", ""),
            negative_prompt=data.get("negative_prompt", ""),
            short_version_lyrics=data.get("short_version_lyrics", ""),
            full_version_lyrics=data.get("full_version_lyrics", ""),
        )
    except Exception as exc:
        logger.warning("Suno prompt generation failed: %s", exc)
        # Fallback: construct a basic prompt from available data
        return _fallback_prompt(tutorial, lyrics, music_spec)


def _fallback_prompt(
    tutorial: TutorialResult,
    lyrics: LyricDraft,
    spec: MusicSpec,
) -> SunoPrompt:
    """Build a basic Suno prompt without LLM assistance."""
    style_parts = []
    if spec.genre:
        style_parts.append(spec.genre)
    if spec.vocal_style:
        style_parts.append(spec.vocal_style)
    if spec.mood:
        style_parts.append(spec.mood)
    if spec.instruments:
        style_parts.append(", ".join(spec.instruments[:3]))
    style_parts.append("educational, fun, catchy")

    formatted_lyrics = ""
    if lyrics.full_text:
        formatted_lyrics = lyrics.full_text
    else:
        parts = []
        for i, v in enumerate(lyrics.verses, 1):
            parts.append(f"[Verse {i}]\n{v}")
        if lyrics.chorus:
            parts.append(f"[Chorus]\n{lyrics.chorus}")
        if lyrics.bridge:
            parts.append(f"[Bridge]\n{lyrics.bridge}")
        formatted_lyrics = "\n\n".join(parts)

    short = ""
    if lyrics.chorus:
        v1 = lyrics.verses[0] if lyrics.verses else ""
        short = f"[Verse]\n{v1}\n\n[Chorus]\n{lyrics.chorus}"

    return SunoPrompt(
        title=f"Learn {tutorial.title} (Song Tutorial)",
        style_prompt=", ".join(style_parts),
        lyrics=formatted_lyrics,
        negative_prompt="avoid mumbling, avoid off-key vocals, avoid distortion, avoid explicit content",
        short_version_lyrics=short,
        full_version_lyrics=formatted_lyrics,
    )
