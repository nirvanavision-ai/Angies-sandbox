"""Main orchestration pipeline — ties all modules together."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from trendbot.critique.concept_engine import generate_concepts
from trendbot.critique.self_critique import critique_tutorial
from trendbot.llm import LLMClient, get_llm_client
from trendbot.lyricist.songwriter import design_music_spec, write_lyrics
from trendbot.models import (
    Niche,
    RunSnapshot,
    ScoringWeights,
    TutorialPackage,
    TutorialResult,
)
from trendbot.prompts.suno import generate_suno_prompt
from trendbot.prompts.viral_packaging import generate_viral_packaging
from trendbot.providers.registry import get_available_providers, run_all_providers
from trendbot.ranking.niche_classifier import classify_niche
from trendbot.ranking.scorer import count_cross_platform, deduplicate, score_tutorial
from trendbot.reporting import save_report
from trendbot.storage.db import TrendBotDB

logger = logging.getLogger(__name__)


# Default niche queries — what to search for in each niche
NICHE_QUERIES: dict[str, list[str]] = {
    "ai": ["AI tutorial 2025", "machine learning beginner guide", "ChatGPT tips tutorial"],
    "coding": ["coding tutorial trending", "python project tutorial", "web dev tutorial 2025"],
    "personal_development": ["personal development tutorial", "productivity system tutorial"],
    "ai_filmmaking": ["AI filmmaking tutorial", "Runway ML tutorial", "AI video generation guide"],
    "graphic_design": ["graphic design tutorial 2025", "Figma tutorial", "logo design tutorial"],
    "finance": ["finance tutorial trending", "investing for beginners", "passive income tutorial"],
    "image_to_video": ["image to video AI tutorial", "stable video diffusion tutorial"],
    "ai_agents": ["AI agents tutorial", "LangChain tutorial 2025", "build AI agent guide"],
    "ai_music": ["AI music tutorial", "Suno tutorial", "Udio tutorial", "AI song creation"],
    "productivity": ["productivity system tutorial", "Notion tutorial 2025", "automation tutorial"],
    "no_code": ["no code tutorial", "Bubble tutorial", "build app without coding"],
    "3d_modeling": ["Blender tutorial 2025", "3D modeling beginner", "Unreal Engine tutorial"],
    "marketing": ["digital marketing tutorial", "SEO tutorial 2025", "content marketing guide"],
}


async def discover(
    niches: list[str],
    *,
    limit: int = 100,
    days: int = 30,
) -> list[TutorialResult]:
    """Phase 1: Discover tutorials across niches from all providers."""
    providers = get_available_providers()
    if not providers:
        logger.warning("No providers available — returning empty results")
        return []

    all_results: list[TutorialResult] = []
    for niche in niches:
        queries = NICHE_QUERIES.get(niche, [f"{niche} tutorial trending"])
        for query in queries:
            results = await run_all_providers(query, providers=providers, limit=limit // len(queries))
            # Classify niche for results
            for r in results:
                if r.niche == Niche.OTHER:
                    r.niche = classify_niche(r.title, r.description)
            all_results.extend(results)

    # Deduplicate
    deduped = deduplicate(all_results)
    logger.info("Discovery: %d raw -> %d deduped results", len(all_results), len(deduped))
    return deduped


async def rank(
    results: list[TutorialResult],
    *,
    weights: ScoringWeights | None = None,
    top_n: int = 20,
    db: TrendBotDB | None = None,
    run_id: str = "",
) -> list[tuple[TutorialResult, Any]]:
    """Phase 2: Score and rank tutorials."""
    w = weights or ScoringWeights()
    cp_counts = count_cross_platform(results)

    scored: list[tuple[TutorialResult, Any]] = []
    for t in results:
        historical = []
        if db and run_id:
            historical = db.get_previous_scores(t.fingerprint, run_id)

        score = score_tutorial(
            t,
            weights=w,
            historical_scores=historical,
            cross_platform_count=cp_counts.get(t.fingerprint, 1),
        )
        scored.append((t, score))

    scored.sort(key=lambda x: x[1].final_score, reverse=True)
    return scored[:top_n]


async def generate_package(
    tutorial: TutorialResult,
    score: Any,
    llm: LLMClient,
    *,
    style: str = "",
    platform: str = "suno",
    skip_llm: bool = False,
) -> TutorialPackage:
    """Phase 3: Generate the full output package for one tutorial."""
    pkg = TutorialPackage(tutorial=tutorial, score=score)

    if skip_llm:
        pkg.why_trending = "Score-based ranking (LLM critique skipped)"
        return pkg

    # Run critique, concepts, lyrics, music spec in parallel where possible
    critique_task = critique_tutorial(
        tutorial, llm,
        recency_score=score.recency,
        engagement_score=score.engagement,
        cross_platform=1,
    )
    concepts_task = generate_concepts(tutorial, llm, topic=tutorial.niche.value)

    critique_result, concepts = await asyncio.gather(critique_task, concepts_task)

    pkg.critique = critique_result
    pkg.concepts = concepts
    pkg.why_trending = "; ".join(critique_result.reasons) if critique_result.reasons else "High combined score"

    # Sequential: lyrics depend on tutorial content, suno prompt depends on lyrics
    lyrics = await write_lyrics(tutorial, llm, style=style or "pop")
    music_spec = await design_music_spec(tutorial, llm, style=style)
    suno_prompt = await generate_suno_prompt(tutorial, lyrics, music_spec, llm, platform=platform)
    viral = await generate_viral_packaging(
        tutorial, llm,
        why_trending=pkg.why_trending,
        genre=music_spec.genre,
    )

    pkg.lyrics = lyrics
    pkg.music_spec = music_spec
    pkg.suno_prompt = suno_prompt
    pkg.viral_packaging = viral

    return pkg


async def run_pipeline(
    niches: list[str],
    *,
    limit: int = 100,
    top_n: int = 20,
    generate_top: int = 5,
    style: str = "",
    platform: str = "suno",
    output_dir: str = "./output",
    weights: ScoringWeights | None = None,
    llm_provider: str | None = None,
    skip_llm: bool = False,
    db_path: str = "./trendbot.db",
) -> list[TutorialPackage]:
    """End-to-end pipeline: discover -> rank -> generate -> report."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    db = TrendBotDB(db_path)
    llm = get_llm_client(llm_provider)

    logger.info("=== TrendBot Run %s ===", run_id)
    logger.info("Niches: %s", niches)

    # Phase 1: Discover
    logger.info("Phase 1: Discovering tutorials...")
    results = await discover(niches, limit=limit)

    if not results:
        logger.warning("No results found — check API keys and providers")
        db.close()
        return []

    # Phase 2: Rank
    logger.info("Phase 2: Ranking %d tutorials...", len(results))
    ranked = await rank(results, weights=weights, top_n=top_n, db=db, run_id=run_id)

    # Save all ranked tutorials to DB
    for t, s in ranked:
        db.save_tutorial(t, run_id, s)

    # Phase 3: Generate packages for top N
    top_for_gen = ranked[:generate_top]
    logger.info("Phase 3: Generating packages for top %d...", len(top_for_gen))

    packages: list[TutorialPackage] = []
    for t, s in top_for_gen:
        pkg = await generate_package(
            t, s, llm, style=style, platform=platform, skip_llm=skip_llm
        )
        packages.append(pkg)
        db.save_package(t.fingerprint, run_id, pkg.model_dump_json())

    # Save run snapshot
    snapshot = RunSnapshot(
        run_id=run_id,
        niches=niches,
        total_results=len(results),
        top_fingerprints=[t.fingerprint for t, _ in ranked],
    )
    db.save_run(snapshot)

    # Phase 4: Generate reports
    logger.info("Phase 4: Saving reports...")
    files = save_report(packages, run_id=run_id, output_dir=output_dir)
    for f in files:
        logger.info("Report saved: %s", f)

    db.close()
    return packages


async def generate_single(
    url: str,
    *,
    style: str = "",
    platform: str = "suno",
    llm_provider: str | None = None,
) -> TutorialPackage:
    """Generate a song package for a single tutorial URL."""
    llm = get_llm_client(llm_provider)

    tutorial = TutorialResult(
        title=f"Tutorial from {url}",
        url=url,
    )

    # Classify niche
    tutorial.niche = classify_niche(tutorial.title, tutorial.description)

    # Create a basic score
    from trendbot.models import ScoreBreakdown
    score = ScoreBreakdown(final_score=0.5)

    return await generate_package(tutorial, score, llm, style=style, platform=platform)
