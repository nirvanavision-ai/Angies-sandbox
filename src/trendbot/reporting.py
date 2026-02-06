"""Report generation — Markdown + JSON output for tutorial packages."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from trendbot.models import TutorialPackage


def render_markdown(packages: list[TutorialPackage], *, run_id: str = "") -> str:
    """Render a full Markdown report for a set of tutorial packages."""
    lines: list[str] = []
    lines.append(f"# TrendBot Report")
    lines.append(f"**Run ID:** {run_id}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Total Tutorials:** {len(packages)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Top Tutorials by Score")
    lines.append("")
    lines.append("| # | Score | Title | Niche | Platform |")
    lines.append("|---|-------|-------|-------|----------|")
    for i, pkg in enumerate(packages, 1):
        t = pkg.tutorial
        lines.append(
            f"| {i} | {pkg.score.final_score:.3f} | "
            f"[{_trunc(t.title, 50)}]({t.url}) | "
            f"{t.niche.value} | {t.platform.value} |"
        )
    lines.append("")

    # Detailed sections
    for i, pkg in enumerate(packages, 1):
        t = pkg.tutorial
        lines.append(f"---")
        lines.append(f"## {i}. {t.title}")
        lines.append("")

        # Metadata
        lines.append("### Metadata")
        lines.append(f"- **URL:** {t.url}")
        lines.append(f"- **Platform:** {t.platform.value}")
        lines.append(f"- **Niche:** {t.niche.value}")
        if t.publish_date:
            lines.append(f"- **Published:** {t.publish_date.strftime('%Y-%m-%d')}")
        if t.view_count is not None:
            lines.append(f"- **Views:** {t.view_count:,}")
        if t.like_count is not None:
            lines.append(f"- **Likes:** {t.like_count:,}")
        lines.append("")

        # Score breakdown
        lines.append("### Score Breakdown")
        s = pkg.score
        lines.append(f"- Recency: {s.recency:.3f}")
        lines.append(f"- Engagement: {s.engagement:.3f}")
        lines.append(f"- Authority: {s.authority:.3f}")
        lines.append(f"- Trend bonus: {s.trend_bonus:.3f}")
        lines.append(f"- Cross-platform bonus: {s.cross_platform_bonus:.3f}")
        lines.append(f"- **Base score: {s.base_score:.3f}**")
        lines.append(f"- **Final score: {s.final_score:.3f}**")
        lines.append("")

        # Why trending
        if pkg.why_trending:
            lines.append("### Why Trending")
            lines.append(pkg.why_trending)
            lines.append("")

        # Critique
        if pkg.critique.is_trend:
            c = pkg.critique
            lines.append("### Trend Critique")
            lines.append(f"- **Is trend:** {c.is_trend} (confidence: {c.confidence:.0%})")
            lines.append(f"- **Type:** {c.trend_type.value}")
            if c.reasons:
                lines.append(f"- **Reasons:** {'; '.join(c.reasons)}")
            if c.red_flags:
                lines.append(f"- **Red flags:** {'; '.join(c.red_flags)}")
            lines.append("")

        # Concepts
        if pkg.concepts:
            lines.append("### Content Concepts")
            for j, concept in enumerate(pkg.concepts, 1):
                lines.append(f"#### Concept {j}")
                lines.append(f"- **Hook:** {concept.hook}")
                lines.append(f"- **Angle:** {concept.angle}")
                lines.append(f"- **Comedic twist:** {concept.comedic_twist}")
                lines.append(f"- **Format:** {concept.format}")
                lines.append(f"- **Why viral:** {concept.why_viral}")
                lines.append("")

        # Lyrics
        if pkg.lyrics.full_text:
            lines.append("### Song Lyrics")
            lines.append("```")
            lines.append(pkg.lyrics.full_text)
            lines.append("```")
            lines.append("")

        # Music spec
        if pkg.music_spec.genre:
            ms = pkg.music_spec
            lines.append("### Music Specification")
            lines.append(f"- **Genre:** {ms.genre}")
            lines.append(f"- **BPM:** {ms.bpm_range}")
            lines.append(f"- **Instruments:** {', '.join(ms.instruments)}")
            lines.append(f"- **Vocal style:** {ms.vocal_style}")
            lines.append(f"- **Mood:** {ms.mood}")
            lines.append("")

        # Suno prompt
        if pkg.suno_prompt.style_prompt:
            sp = pkg.suno_prompt
            lines.append("### Suno Prompt")
            lines.append(f"**Title:** {sp.title}")
            lines.append(f"**Style:** {sp.style_prompt}")
            if sp.negative_prompt:
                lines.append(f"**Negative:** {sp.negative_prompt}")
            lines.append("")
            lines.append("**Short version (45s):**")
            lines.append("```")
            lines.append(sp.short_version_lyrics)
            lines.append("```")
            lines.append("")
            lines.append("**Full version:**")
            lines.append("```")
            lines.append(sp.full_version_lyrics)
            lines.append("```")
            lines.append("")

        # Viral packaging
        if pkg.viral_packaging.suggested_title:
            vp = pkg.viral_packaging
            lines.append("### Viral Packaging")
            lines.append(f"- **Title:** {vp.suggested_title}")
            lines.append(f"- **10s hook:** {vp.ten_second_hook_script}")
            lines.append(f"- **Thumbnail ideas:** {', '.join(vp.thumbnail_text_ideas)}")
            lines.append(f"- **TikTok caption:** {vp.tiktok_caption}")
            lines.append(f"- **Hashtags:** {' '.join(vp.hashtags)}")
            lines.append("")

    return "\n".join(lines)


def render_json(packages: list[TutorialPackage], *, run_id: str = "") -> str:
    """Render packages as JSON."""
    output = {
        "run_id": run_id,
        "generated": datetime.now(timezone.utc).isoformat(),
        "total": len(packages),
        "packages": [p.model_dump(mode="json") for p in packages],
    }
    return json.dumps(output, indent=2, default=str)


def save_report(
    packages: list[TutorialPackage],
    *,
    run_id: str = "",
    output_dir: str = "./output",
    formats: list[str] | None = None,
) -> list[str]:
    """Save reports to files. Returns list of created file paths."""
    formats = formats or ["md", "json"]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    if "md" in formats:
        md_path = out / f"report_{run_id}.md"
        md_path.write_text(render_markdown(packages, run_id=run_id))
        created.append(str(md_path))

    if "json" in formats:
        json_path = out / f"report_{run_id}.json"
        json_path.write_text(render_json(packages, run_id=run_id))
        created.append(str(json_path))

    return created


def _trunc(s: str, n: int) -> str:
    return s[:n] + "..." if len(s) > n else s
