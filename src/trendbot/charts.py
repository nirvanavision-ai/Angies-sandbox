"""Chart generation from SQLite data — trend velocity, score distributions, etc."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_charts(
    db_path: str = "./trendbot.db",
    output_dir: str = "./output/charts",
) -> list[str]:
    """Generate PNG charts from stored data. Returns list of created file paths."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not installed — skipping chart generation")
        return []

    from trendbot.storage.db import TrendBotDB

    db = TrendBotDB(db_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    runs = db.get_runs(limit=10)
    if not runs:
        logger.info("No runs found in DB — nothing to chart")
        db.close()
        return []

    # Chart 1: Score distribution for the latest run
    latest = runs[0]
    tutorials = db.get_tutorials_for_run(latest.run_id, limit=100)
    if tutorials:
        scores = [t["final_score"] for t in tutorials]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(scores, bins=20, color="#4C72B0", edgecolor="white", alpha=0.8)
        ax.set_title(f"Score Distribution — Run {latest.run_id[:8]}", fontsize=14)
        ax.set_xlabel("Final Score")
        ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.3)
        path = out / "score_distribution.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        created.append(str(path))

    # Chart 2: Top tutorials bar chart
    if tutorials:
        top = tutorials[:15]
        fig, ax = plt.subplots(figsize=(12, 6))
        titles = [_trunc(t["title"], 40) for t in top]
        scores = [t["final_score"] for t in top]
        bars = ax.barh(range(len(titles)), scores, color="#4C72B0", alpha=0.8)
        ax.set_yticks(range(len(titles)))
        ax.set_yticklabels(titles, fontsize=8)
        ax.set_xlabel("Final Score")
        ax.set_title("Top Tutorials by Score", fontsize=14)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)
        path = out / "top_tutorials.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        created.append(str(path))

    # Chart 3: Week-over-week delta (if we have 2+ runs)
    if len(runs) >= 2:
        deltas = db.compute_week_delta(runs[0].run_id, runs[1].run_id)
        if deltas:
            movers = deltas[:10]
            fig, ax = plt.subplots(figsize=(12, 6))
            titles = [_trunc(d["title"], 40) for d in movers]
            delta_vals = [d["delta"] for d in movers]
            colors = ["#2ecc71" if d > 0 else "#e74c3c" for d in delta_vals]
            ax.barh(range(len(titles)), delta_vals, color=colors, alpha=0.8)
            ax.set_yticks(range(len(titles)))
            ax.set_yticklabels(titles, fontsize=8)
            ax.set_xlabel("Score Change")
            ax.set_title("Biggest Movers (Week-over-Week)", fontsize=14)
            ax.invert_yaxis()
            ax.axvline(x=0, color="gray", linewidth=0.5)
            ax.grid(axis="x", alpha=0.3)
            path = out / "week_delta.png"
            fig.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            created.append(str(path))

    # Chart 4: Niche breakdown pie chart
    if tutorials:
        niche_counts: dict[str, int] = {}
        for t in tutorials:
            n = t.get("niche", "other")
            niche_counts[n] = niche_counts.get(n, 0) + 1
        fig, ax = plt.subplots(figsize=(8, 8))
        labels = list(niche_counts.keys())
        sizes = list(niche_counts.values())
        ax.pie(sizes, labels=labels, autopct="%1.0f%%", startangle=140)
        ax.set_title("Tutorial Distribution by Niche", fontsize=14)
        path = out / "niche_breakdown.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        created.append(str(path))

    db.close()
    return created


def _trunc(s: str, n: int) -> str:
    return s[:n] + "..." if len(s) > n else s
