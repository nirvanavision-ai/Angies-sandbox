"""SQLite storage for TrendBot runs, snapshots, and week-over-week deltas."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trendbot.models import RunSnapshot, ScoreBreakdown, TutorialResult


_DEFAULT_DB = os.environ.get("TRENDBOT_DB_PATH", "./trendbot.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    niches TEXT NOT NULL,
    total_results INTEGER NOT NULL DEFAULT 0,
    top_fingerprints TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS tutorials (
    fingerprint TEXT NOT NULL,
    run_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'web',
    niche TEXT NOT NULL DEFAULT 'other',
    publish_date TEXT,
    description TEXT NOT NULL DEFAULT '',
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    provider_source TEXT NOT NULL DEFAULT '',
    final_score REAL NOT NULL DEFAULT 0.0,
    score_breakdown TEXT NOT NULL DEFAULT '{}',
    raw_metadata TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (fingerprint, run_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS packages (
    fingerprint TEXT NOT NULL,
    run_id TEXT NOT NULL,
    package_json TEXT NOT NULL,
    PRIMARY KEY (fingerprint, run_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_tutorials_run ON tutorials(run_id);
CREATE INDEX IF NOT EXISTS idx_tutorials_niche ON tutorials(niche);
CREATE INDEX IF NOT EXISTS idx_tutorials_score ON tutorials(final_score DESC);
"""


class TrendBotDB:
    """Thin wrapper around SQLite for persistence."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---- Runs ----

    def save_run(self, snapshot: RunSnapshot) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, timestamp, niches, total_results, top_fingerprints) VALUES (?,?,?,?,?)",
            (
                snapshot.run_id,
                snapshot.timestamp.isoformat(),
                json.dumps(snapshot.niches),
                snapshot.total_results,
                json.dumps(snapshot.top_fingerprints),
            ),
        )
        self._conn.commit()

    def get_runs(self, limit: int = 50) -> list[RunSnapshot]:
        rows = self._conn.execute(
            "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            RunSnapshot(
                run_id=r["run_id"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                niches=json.loads(r["niches"]),
                total_results=r["total_results"],
                top_fingerprints=json.loads(r["top_fingerprints"]),
            )
            for r in rows
        ]

    # ---- Tutorials ----

    def save_tutorial(
        self, t: TutorialResult, run_id: str, score: ScoreBreakdown
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO tutorials
            (fingerprint, run_id, title, url, canonical_url, platform, niche,
             publish_date, description, view_count, like_count, comment_count,
             provider_source, final_score, score_breakdown, raw_metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                t.fingerprint,
                run_id,
                t.title,
                t.url,
                t.canonical_url,
                t.platform.value,
                t.niche.value,
                t.publish_date.isoformat() if t.publish_date else None,
                t.description,
                t.view_count,
                t.like_count,
                t.comment_count,
                t.provider_source,
                score.final_score,
                score.model_dump_json(),
                json.dumps(t.raw_metadata),
            ),
        )
        self._conn.commit()

    def get_tutorials_for_run(self, run_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM tutorials WHERE run_id = ? ORDER BY final_score DESC LIMIT ?",
            (run_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_previous_scores(self, fingerprint: str, exclude_run: str, limit: int = 5) -> list[float]:
        """Get historical scores for a tutorial to compute velocity."""
        rows = self._conn.execute(
            """SELECT final_score FROM tutorials
               WHERE fingerprint = ? AND run_id != ?
               ORDER BY rowid DESC LIMIT ?""",
            (fingerprint, exclude_run, limit),
        ).fetchall()
        return [r["final_score"] for r in rows]

    # ---- Packages ----

    def save_package(self, fingerprint: str, run_id: str, package_json: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO packages (fingerprint, run_id, package_json) VALUES (?,?,?)",
            (fingerprint, run_id, package_json),
        )
        self._conn.commit()

    def get_package(self, fingerprint: str, run_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT package_json FROM packages WHERE fingerprint = ? AND run_id = ?",
            (fingerprint, run_id),
        ).fetchone()
        return row["package_json"] if row else None

    # ---- Deltas ----

    def compute_week_delta(self, current_run: str, previous_run: str) -> list[dict[str, Any]]:
        """Compare scores between two runs to find movers."""
        cur = {
            r["fingerprint"]: r
            for r in self.get_tutorials_for_run(current_run, limit=500)
        }
        prev = {
            r["fingerprint"]: r
            for r in self.get_tutorials_for_run(previous_run, limit=500)
        }
        deltas = []
        for fp, row in cur.items():
            prev_score = prev[fp]["final_score"] if fp in prev else 0.0
            delta = row["final_score"] - prev_score
            deltas.append({
                "fingerprint": fp,
                "title": row["title"],
                "current_score": row["final_score"],
                "previous_score": prev_score,
                "delta": delta,
                "is_new": fp not in prev,
            })
        deltas.sort(key=lambda d: d["delta"], reverse=True)
        return deltas

    def close(self) -> None:
        self._conn.close()
