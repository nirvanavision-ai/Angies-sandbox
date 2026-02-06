"""Tests for SQLite storage layer."""

import json
import os
import tempfile

import pytest

from trendbot.models import RunSnapshot, ScoreBreakdown, TutorialResult
from trendbot.storage.db import TrendBotDB


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = TrendBotDB(path)
    yield database
    database.close()
    os.unlink(path)


class TestTrendBotDB:
    def test_save_and_get_run(self, db: TrendBotDB):
        snap = RunSnapshot(
            run_id="test_run_001",
            niches=["ai", "coding"],
            total_results=42,
            top_fingerprints=["fp1", "fp2"],
        )
        db.save_run(snap)
        runs = db.get_runs(limit=10)
        assert len(runs) == 1
        assert runs[0].run_id == "test_run_001"
        assert runs[0].niches == ["ai", "coding"]
        assert runs[0].total_results == 42

    def test_save_and_get_tutorial(self, db: TrendBotDB):
        t = TutorialResult(
            title="Test Tutorial",
            url="https://example.com/test",
            view_count=1000,
        )
        score = ScoreBreakdown(final_score=0.75, recency=0.8, engagement=0.6, authority=0.5)
        db.save_tutorial(t, "run_001", score)

        tutorials = db.get_tutorials_for_run("run_001")
        assert len(tutorials) == 1
        assert tutorials[0]["title"] == "Test Tutorial"
        assert tutorials[0]["final_score"] == 0.75

    def test_get_previous_scores(self, db: TrendBotDB):
        t = TutorialResult(title="Tutorial", url="https://example.com/t")
        # Save across multiple runs
        db.save_tutorial(t, "run_01", ScoreBreakdown(final_score=0.3))
        db.save_tutorial(t, "run_02", ScoreBreakdown(final_score=0.5))
        db.save_tutorial(t, "run_03", ScoreBreakdown(final_score=0.7))

        scores = db.get_previous_scores(t.fingerprint, "run_03", limit=5)
        assert len(scores) == 2
        assert 0.3 in scores
        assert 0.5 in scores

    def test_save_and_get_package(self, db: TrendBotDB):
        db.save_package("fp_001", "run_001", '{"test": true}')
        result = db.get_package("fp_001", "run_001")
        assert result == '{"test": true}'

    def test_get_package_missing(self, db: TrendBotDB):
        result = db.get_package("nonexistent", "nonexistent")
        assert result is None

    def test_compute_week_delta(self, db: TrendBotDB):
        t1 = TutorialResult(title="Rising", url="https://example.com/rise")
        t2 = TutorialResult(title="Falling", url="https://example.com/fall")

        db.save_tutorial(t1, "week1", ScoreBreakdown(final_score=0.3))
        db.save_tutorial(t2, "week1", ScoreBreakdown(final_score=0.8))
        db.save_tutorial(t1, "week2", ScoreBreakdown(final_score=0.9))
        db.save_tutorial(t2, "week2", ScoreBreakdown(final_score=0.4))

        deltas = db.compute_week_delta("week2", "week1")
        assert len(deltas) == 2
        # Rising tutorial should have positive delta
        rising = [d for d in deltas if d["title"] == "Rising"][0]
        falling = [d for d in deltas if d["title"] == "Falling"][0]
        assert rising["delta"] > 0
        assert falling["delta"] < 0

    def test_multiple_runs_ordered(self, db: TrendBotDB):
        from datetime import datetime, timezone, timedelta

        snap1 = RunSnapshot(
            run_id="old_run",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        snap2 = RunSnapshot(
            run_id="new_run",
            timestamp=datetime.now(timezone.utc),
        )
        db.save_run(snap1)
        db.save_run(snap2)
        runs = db.get_runs(limit=10)
        assert runs[0].run_id == "new_run"  # Most recent first
