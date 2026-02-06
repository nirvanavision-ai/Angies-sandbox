"""Core data models for TrendBot."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

from pydantic import BaseModel, Field, field_validator


class Niche(str, Enum):
    AI = "ai"
    CODING = "coding"
    PERSONAL_DEV = "personal_development"
    AI_FILMMAKING = "ai_filmmaking"
    GRAPHIC_DESIGN = "graphic_design"
    FINANCE = "finance"
    IMAGE_TO_VIDEO = "image_to_video"
    AI_AGENTS = "ai_agents"
    AI_MUSIC = "ai_music"
    PRODUCTIVITY = "productivity"
    NO_CODE = "no_code"
    THREE_D = "3d_modeling"
    MARKETING = "marketing"
    OTHER = "other"


class Platform(str, Enum):
    YOUTUBE = "youtube"
    MEDIUM = "medium"
    SUBSTACK = "substack"
    GITHUB = "github"
    REDDIT = "reddit"
    TWITTER = "twitter"
    WEB = "web"
    DEV_TO = "dev_to"
    HACKERNEWS = "hackernews"


class TrendType(str, Enum):
    EMERGING = "emerging"
    GROWING = "growing"
    PEAKING = "peaking"
    SUSTAINED = "sustained"
    FADING = "fading"


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------

_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def normalize_url(raw: str) -> str:
    """Canonicalize a URL for dedup purposes."""
    raw = raw.strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    scheme = "https"
    host = (parsed.hostname or "").lower().rstrip(".")
    path = re.sub(r"/+", "/", parsed.path.rstrip("/")) or "/"
    # YouTube special handling
    if host in _YT_HOSTS:
        vid = extract_youtube_id(raw)
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"
    # Strip tracking params
    keep_params: dict[str, list[str]] = {}
    for k, v in parse_qs(parsed.query, keep_blank_values=False).items():
        if k.lower() not in {
            "utm_source", "utm_medium", "utm_campaign", "utm_term",
            "utm_content", "ref", "fbclid", "gclid", "mc_cid", "mc_eid",
        }:
            keep_params[k] = v
    query = "&".join(f"{k}={v[0]}" for k, v in sorted(keep_params.items()))
    return urlunparse((scheme, host, path, "", query, ""))


def extract_youtube_id(url: str) -> str | None:
    """Extract a YouTube video ID from various URL formats."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        vid = parsed.path.lstrip("/").split("/")[0]
        return vid if vid else None
    if host in _YT_HOSTS:
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
        parts = parsed.path.split("/")
        for i, seg in enumerate(parts):
            if seg in ("embed", "v", "shorts") and i + 1 < len(parts):
                return parts[i + 1]
    return None


def content_fingerprint(title: str, url: str) -> str:
    """Create a dedup fingerprint from title + canonical URL."""
    canon = normalize_url(url)
    blob = f"{title.lower().strip()}|{canon}"
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class TutorialResult(BaseModel):
    """A single tutorial discovered from a provider."""
    title: str
    url: str
    canonical_url: str = ""
    fingerprint: str = ""
    platform: Platform = Platform.WEB
    niche: Niche = Niche.OTHER
    publish_date: datetime | None = None
    description: str = ""
    transcript: str = ""
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    provider_source: str = ""
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, _: Any) -> None:
        if not self.canonical_url:
            self.canonical_url = normalize_url(self.url)
        if not self.fingerprint:
            self.fingerprint = content_fingerprint(self.title, self.url)


class ScoreBreakdown(BaseModel):
    recency: float = 0.0
    engagement: float = 0.0
    authority: float = 0.0
    trend_bonus: float = 0.0
    cross_platform_bonus: float = 0.0
    base_score: float = 0.0
    final_score: float = 0.0


class CritiqueResult(BaseModel):
    is_trend: bool = False
    confidence: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    what_to_verify: list[str] = Field(default_factory=list)
    trend_type: TrendType = TrendType.EMERGING


class ConceptIdea(BaseModel):
    hook: str = ""
    angle: str = ""
    comedic_twist: str = ""
    format: str = ""
    why_viral: str = ""


class MusicSpec(BaseModel):
    genre: str = ""
    bpm_range: str = ""
    instruments: list[str] = Field(default_factory=list)
    vocal_style: str = ""
    vocal_references: list[str] = Field(default_factory=list)
    mood: str = ""


class LyricDraft(BaseModel):
    verses: list[str] = Field(default_factory=list)
    chorus: str = ""
    bridge: str = ""
    rap_breakdown: str = ""
    step_callouts: list[str] = Field(default_factory=list)
    full_text: str = ""


class SunoPrompt(BaseModel):
    title: str = ""
    style_prompt: str = ""
    lyrics: str = ""
    negative_prompt: str = ""
    short_version_lyrics: str = ""
    full_version_lyrics: str = ""


class ViralPackaging(BaseModel):
    suggested_title: str = ""
    ten_second_hook_script: str = ""
    thumbnail_text_ideas: list[str] = Field(default_factory=list)
    tiktok_caption: str = ""
    hashtags: list[str] = Field(default_factory=list)


class TutorialPackage(BaseModel):
    """Complete output package for a single tutorial."""
    tutorial: TutorialResult
    score: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    why_trending: str = ""
    critique: CritiqueResult = Field(default_factory=CritiqueResult)
    concepts: list[ConceptIdea] = Field(default_factory=list)
    lyrics: LyricDraft = Field(default_factory=LyricDraft)
    music_spec: MusicSpec = Field(default_factory=MusicSpec)
    suno_prompt: SunoPrompt = Field(default_factory=SunoPrompt)
    viral_packaging: ViralPackaging = Field(default_factory=ViralPackaging)


class RunSnapshot(BaseModel):
    """Metadata for a single discovery run, stored in SQLite."""
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    niches: list[str] = Field(default_factory=list)
    total_results: int = 0
    top_fingerprints: list[str] = Field(default_factory=list)


class ScoringWeights(BaseModel):
    recency: float = 0.45
    engagement: float = 0.45
    authority: float = 0.10
    trend_velocity_multiplier: float = 1.5
    cross_platform_bonus: float = 0.15

    @field_validator("recency", "engagement", "authority")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
