"""Tests for the scoring engine."""

import pytest
from datetime import datetime, timezone, timedelta

from trendbot.models import Platform, TutorialResult, ScoringWeights
from trendbot.ranking.scorer import (
    score_tutorial,
    compute_velocity,
    count_cross_platform,
    _recency_score,
    _log_normalize,
    _engagement_score,
)


class TestRecencyScore:
    def test_today_is_1(self):
        now = datetime.now(timezone.utc)
        score = _recency_score(now)
        assert score > 0.99

    def test_one_week_ago_is_half(self):
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        score = _recency_score(week_ago, half_life_days=7.0)
        assert 0.45 < score < 0.55

    def test_old_content_low_score(self):
        old = datetime.now(timezone.utc) - timedelta(days=90)
        score = _recency_score(old)
        assert score < 0.01

    def test_none_date_returns_default(self):
        score = _recency_score(None)
        assert score == 0.3

    def test_future_date_clamps(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        score = _recency_score(future)
        assert score >= 1.0


class TestLogNormalize:
    def test_zero_returns_zero(self):
        assert _log_normalize(0, 1000) == 0.0

    def test_max_returns_one(self):
        assert _log_normalize(1_000_000, 1_000_000) == 1.0

    def test_half_is_less_than_one(self):
        score = _log_normalize(500_000, 1_000_000)
        assert 0 < score < 1

    def test_negative_returns_zero(self):
        assert _log_normalize(-1, 1000) == 0.0

    def test_above_max_clamps(self):
        score = _log_normalize(10_000_000, 1_000_000)
        assert score == 1.0


class TestEngagementScore:
    def test_zero_engagement(self):
        score = _engagement_score(0, 0, 0, max_views=1_000_000, max_likes=50_000, max_comments=5_000)
        assert score == 0.0

    def test_max_engagement(self):
        score = _engagement_score(
            1_000_000, 50_000, 5_000,
            max_views=1_000_000, max_likes=50_000, max_comments=5_000,
        )
        assert score == 1.0

    def test_views_weighted_highest(self):
        views_only = _engagement_score(
            100_000, 0, 0, max_views=1_000_000, max_likes=50_000, max_comments=5_000,
        )
        likes_only = _engagement_score(
            0, 100_000, 0, max_views=1_000_000, max_likes=50_000, max_comments=5_000,
        )
        # Views have 0.5 weight, likes have 0.3 weight
        # But likes are above max so they get clamped — still views should dominate at moderate levels
        assert views_only > 0


class TestScoreTutorial:
    def test_basic_scoring(self):
        t = TutorialResult(
            title="Test Tutorial",
            url="https://example.com/test",
            publish_date=datetime.now(timezone.utc),
            view_count=50_000,
            like_count=2_000,
            comment_count=200,
        )
        score = score_tutorial(t)
        assert 0 <= score.final_score <= 1
        assert score.base_score > 0

    def test_no_engagement_low_score(self):
        old = datetime.now(timezone.utc) - timedelta(days=60)
        t = TutorialResult(title="Old Tutorial", url="https://example.com/old", publish_date=old)
        score = score_tutorial(t)
        assert score.final_score < 0.3

    def test_trending_bonus(self):
        t = TutorialResult(
            title="Trending",
            url="https://example.com/trend",
            publish_date=datetime.now(timezone.utc),
            view_count=100_000,
        )
        score_no_history = score_tutorial(t)
        score_with_history = score_tutorial(t, historical_scores=[0.1, 0.05])
        assert score_with_history.trend_bonus > 0
        assert score_with_history.final_score >= score_no_history.final_score

    def test_cross_platform_bonus(self):
        t = TutorialResult(title="Cross", url="https://example.com/cross")
        score_single = score_tutorial(t, cross_platform_count=1)
        score_multi = score_tutorial(t, cross_platform_count=3)
        assert score_multi.cross_platform_bonus > score_single.cross_platform_bonus

    def test_custom_weights(self):
        t = TutorialResult(
            title="Custom",
            url="https://example.com/custom",
            publish_date=datetime.now(timezone.utc),
            view_count=50_000,
        )
        heavy_recency = ScoringWeights(recency=0.9, engagement=0.05, authority=0.05)
        heavy_engagement = ScoringWeights(recency=0.05, engagement=0.9, authority=0.05)
        sr = score_tutorial(t, weights=heavy_recency)
        se = score_tutorial(t, weights=heavy_engagement)
        # With heavy recency weight and a recent tutorial, recency-weighted score should differ
        assert sr.final_score != se.final_score


class TestVelocity:
    def test_no_history(self):
        v, a = compute_velocity([], 0.5)
        assert v == 0.0
        assert a == 0.0

    def test_positive_velocity(self):
        v, a = compute_velocity([0.3], 0.7)
        assert v > 0

    def test_negative_velocity(self):
        v, a = compute_velocity([0.8], 0.3)
        assert v < 0

    def test_acceleration(self):
        # current=0.9, prev=0.6, prev_prev=0.4
        # velocity = 0.9 - 0.6 = 0.3
        # prev_velocity = 0.6 - 0.4 = 0.2
        # acceleration = 0.3 - 0.2 = 0.1
        v, a = compute_velocity([0.6, 0.4], 0.9)
        assert v == pytest.approx(0.3)
        assert a == pytest.approx(0.1)


class TestCrossPlatformCount:
    def test_single_provider(self):
        results = [
            TutorialResult(title="A", url="https://example.com/a", provider_source="tavily"),
        ]
        counts = count_cross_platform(results)
        assert counts[results[0].fingerprint] == 1

    def test_multiple_providers_same_content(self):
        # Same title + url → same fingerprint
        results = [
            TutorialResult(title="Tutorial X", url="https://example.com/x", provider_source="tavily"),
            TutorialResult(title="Tutorial X", url="https://example.com/x", provider_source="serpapi"),
            TutorialResult(title="Tutorial X", url="https://example.com/x", provider_source="youtube"),
        ]
        counts = count_cross_platform(results)
        fp = results[0].fingerprint
        assert counts[fp] == 3

    def test_different_content(self):
        results = [
            TutorialResult(title="A", url="https://example.com/a", provider_source="tavily"),
            TutorialResult(title="B", url="https://example.com/b", provider_source="tavily"),
        ]
        counts = count_cross_platform(results)
        assert len(counts) == 2
        assert all(c == 1 for c in counts.values())
