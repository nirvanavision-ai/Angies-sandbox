"""Scoring engine for ranking discovered tutorials."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from trendbot.models import ScoreBreakdown, ScoringWeights, TutorialResult


def score_tutorial(
    t: TutorialResult,
    *,
    weights: ScoringWeights | None = None,
    historical_scores: list[float] | None = None,
    cross_platform_count: int = 1,
    max_views: int = 1_000_000,
    max_likes: int = 50_000,
    max_comments: int = 5_000,
) -> ScoreBreakdown:
    """Score a tutorial on [0, 1] with component breakdown."""
    w = weights or ScoringWeights()

    recency = _recency_score(t.publish_date)
    engagement = _engagement_score(
        t.view_count, t.like_count, t.comment_count,
        max_views=max_views, max_likes=max_likes, max_comments=max_comments,
    )
    authority = _authority_proxy(t)

    base = w.recency * recency + w.engagement * engagement + w.authority * authority

    # Trend velocity / acceleration bonus
    trend_bonus = 0.0
    if historical_scores:
        velocity, accel = compute_velocity(historical_scores, base)
        if velocity > 0:
            trend_bonus = min(0.3, velocity * w.trend_velocity_multiplier)
        if accel > 0:
            trend_bonus += min(0.1, accel * 0.5)

    # Cross-platform bonus
    cp_bonus = 0.0
    if cross_platform_count > 1:
        cp_bonus = min(0.3, w.cross_platform_bonus * (cross_platform_count - 1))

    final = min(1.0, base + trend_bonus + cp_bonus)

    return ScoreBreakdown(
        recency=round(recency, 4),
        engagement=round(engagement, 4),
        authority=round(authority, 4),
        trend_bonus=round(trend_bonus, 4),
        cross_platform_bonus=round(cp_bonus, 4),
        base_score=round(base, 4),
        final_score=round(final, 4),
    )


def _recency_score(pub_date: datetime | None, half_life_days: float = 7.0) -> float:
    """Exponential decay: 1.0 for today, ~0.5 at half_life_days ago."""
    if pub_date is None:
        return 0.3  # Unknown date → moderate score
    now = datetime.now(timezone.utc)
    if pub_date.tzinfo is None:
        pub_date = pub_date.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - pub_date).total_seconds() / 86400)
    return math.exp(-0.693 * age_days / half_life_days)


def _engagement_score(
    views: int | None,
    likes: int | None,
    comments: int | None,
    *,
    max_views: int,
    max_likes: int,
    max_comments: int,
) -> float:
    """Normalized engagement score combining views, likes, comments."""
    v = _log_normalize(views or 0, max_views) * 0.5
    l = _log_normalize(likes or 0, max_likes) * 0.3
    c = _log_normalize(comments or 0, max_comments) * 0.2
    return min(1.0, v + l + c)


def _log_normalize(value: int, maximum: int) -> float:
    """Log-scale normalization to prevent outliers from dominating."""
    if value <= 0 or maximum <= 0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(maximum))


def _authority_proxy(t: TutorialResult) -> float:
    """Simple authority heuristic based on platform and metadata."""
    base = 0.3
    # YouTube channels with high engagement get a boost
    if t.platform.value == "youtube" and (t.view_count or 0) > 10_000:
        base += 0.3
    # GitHub with many stars
    if t.platform.value == "github":
        stars = t.raw_metadata.get("stars", 0)
        if stars and stars > 100:
            base += 0.3
    # Known platforms get a small bump
    if t.platform.value in ("youtube", "github", "medium"):
        base += 0.1
    return min(1.0, base)


def compute_velocity(
    historical_scores: list[float], current_score: float
) -> tuple[float, float]:
    """Compute velocity (first derivative) and acceleration (second derivative).

    Returns (velocity, acceleration) where positive = trending up.
    """
    if not historical_scores:
        return 0.0, 0.0

    prev = historical_scores[0]  # most recent historical score
    velocity = current_score - prev

    if len(historical_scores) >= 2:
        prev_velocity = historical_scores[0] - historical_scores[1]
        acceleration = velocity - prev_velocity
    else:
        acceleration = 0.0

    return velocity, acceleration


def deduplicate(results: list[TutorialResult]) -> list[TutorialResult]:
    """Remove duplicates based on fingerprint, keeping first seen."""
    seen: set[str] = set()
    deduped: list[TutorialResult] = []
    for r in results:
        if r.fingerprint not in seen:
            seen.add(r.fingerprint)
            deduped.append(r)
    return deduped


def count_cross_platform(
    results: list[TutorialResult],
) -> dict[str, int]:
    """Count how many distinct providers mention each canonical URL.

    Returns fingerprint -> count mapping.
    """
    fp_providers: dict[str, set[str]] = {}
    for r in results:
        fp_providers.setdefault(r.fingerprint, set()).add(r.provider_source)
    return {fp: len(providers) for fp, providers in fp_providers.items()}
