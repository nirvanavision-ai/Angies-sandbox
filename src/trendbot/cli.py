"""CLI interface for TrendBot."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

load_dotenv()

console = Console()


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )


@click.group()
@click.option("--log-level", default=os.environ.get("TRENDBOT_LOG_LEVEL", "INFO"))
def cli(log_level: str) -> None:
    """TrendBot — Discover trending tutorials and turn them into viral songs."""
    _setup_logging(log_level)


@cli.command()
@click.option("--niches", "-n", default="ai,coding,ai_music", help="Comma-separated niches")
@click.option("--days", "-d", default=30, help="Look back N days")
@click.option("--limit", "-l", default=100, help="Max results per niche query")
@click.option("--output", "-o", default="./output", help="Output directory")
def discover(niches: str, days: int, limit: int, output: str) -> None:
    """Discover trending tutorials across niches."""
    from trendbot.pipeline import discover as _discover

    niche_list = [n.strip() for n in niches.split(",")]
    console.print(f"[bold]Discovering tutorials for niches:[/bold] {niche_list}")

    results = asyncio.run(_discover(niche_list, limit=limit, days=days))

    table = Table(title=f"Discovered {len(results)} tutorials")
    table.add_column("#", style="dim")
    table.add_column("Title", max_width=50)
    table.add_column("Platform")
    table.add_column("Niche")
    table.add_column("Source")
    for i, r in enumerate(results[:50], 1):
        table.add_row(str(i), r.title[:50], r.platform.value, r.niche.value, r.provider_source)
    console.print(table)

    # Save raw results
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "discovered.json"
    data = [r.model_dump(mode="json") for r in results]
    out_file.write_text(json.dumps(data, indent=2, default=str))
    console.print(f"[green]Results saved to {out_file}[/green]")


@cli.command()
@click.option("--input", "-i", "input_file", required=True, help="Path to discovered results JSON")
@click.option("--top", "-t", default=20, help="Number of top results to keep")
@click.option("--output", "-o", default="./output", help="Output directory")
def rank(input_file: str, top: int, output: str) -> None:
    """Rank previously discovered tutorials."""
    from trendbot.models import TutorialResult
    from trendbot.pipeline import rank as _rank

    data = json.loads(Path(input_file).read_text())
    results = [TutorialResult(**d) for d in data]
    console.print(f"[bold]Ranking {len(results)} tutorials (top {top})...[/bold]")

    ranked = asyncio.run(_rank(results, top_n=top))

    table = Table(title=f"Top {len(ranked)} Tutorials")
    table.add_column("#", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Title", max_width=50)
    table.add_column("Niche")
    table.add_column("Platform")
    for i, (t, s) in enumerate(ranked, 1):
        table.add_row(
            str(i), f"{s.final_score:.3f}", t.title[:50], t.niche.value, t.platform.value
        )
    console.print(table)

    # Save ranked
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "ranked.json"
    ranked_data = [
        {"tutorial": t.model_dump(mode="json"), "score": s.model_dump(mode="json")}
        for t, s in ranked
    ]
    out_file.write_text(json.dumps(ranked_data, indent=2, default=str))
    console.print(f"[green]Ranked results saved to {out_file}[/green]")


@cli.command()
@click.option("--tutorial-url", "-u", required=True, help="URL of the tutorial")
@click.option("--style", "-s", default="", help="Musical style (e.g., 'hyperpop', 'lo-fi')")
@click.option("--platform", "-p", default="suno", help="Music platform: suno or udio")
@click.option("--output", "-o", default="./output", help="Output directory")
@click.option("--llm-provider", default=None, help="LLM provider: anthropic or openai")
def generate(tutorial_url: str, style: str, platform: str, output: str, llm_provider: str | None) -> None:
    """Generate a song tutorial for a single URL."""
    from trendbot.pipeline import generate_single
    from trendbot.reporting import save_report

    console.print(f"[bold]Generating song for:[/bold] {tutorial_url}")
    console.print(f"Style: {style or 'auto'} | Platform: {platform}")

    pkg = asyncio.run(generate_single(tutorial_url, style=style, platform=platform, llm_provider=llm_provider))

    # Display summary
    if pkg.suno_prompt.style_prompt:
        console.print(f"\n[bold green]Suno Style Prompt:[/bold green]\n{pkg.suno_prompt.style_prompt}")
    if pkg.lyrics.chorus:
        console.print(f"\n[bold green]Chorus:[/bold green]\n{pkg.lyrics.chorus}")
    if pkg.viral_packaging.suggested_title:
        console.print(f"\n[bold green]Suggested Title:[/bold green] {pkg.viral_packaging.suggested_title}")

    files = save_report([pkg], run_id="single", output_dir=output)
    for f in files:
        console.print(f"[green]Saved: {f}[/green]")


@cli.command("run")
@click.option("--niches", "-n", default="ai,coding,ai_music", help="Comma-separated niches")
@click.option("--topic", "-t", default="", help="Override topic query (used across all niches)")
@click.option("--limit", "-l", default=100, help="Discovery limit per niche query")
@click.option("--top", default=20, help="Top N tutorials to rank")
@click.option("--generate-top", default=5, help="Generate full packages for top N")
@click.option("--style", "-s", default="", help="Musical style override")
@click.option("--platform", "-p", default="suno", help="Music platform: suno or udio")
@click.option("--output", "-o", default="./output", help="Output directory")
@click.option("--llm-provider", default=None, help="LLM provider: anthropic or openai")
@click.option("--skip-llm", is_flag=True, help="Skip LLM calls (scoring only)")
@click.option("--db-path", default="./trendbot.db", help="SQLite database path")
def run(
    niches: str,
    topic: str,
    limit: int,
    top: int,
    generate_top: int,
    style: str,
    platform: str,
    output: str,
    llm_provider: str | None,
    skip_llm: bool,
    db_path: str,
) -> None:
    """End-to-end: discover, rank, generate, and report."""
    from trendbot.pipeline import run_pipeline, NICHE_QUERIES

    niche_list = [n.strip() for n in niches.split(",")]

    # If topic is provided, override queries
    if topic:
        for niche in niche_list:
            NICHE_QUERIES[niche] = [f"{topic} tutorial"]

    console.print(f"[bold]TrendBot End-to-End Run[/bold]")
    console.print(f"Niches: {niche_list}")
    console.print(f"Limit: {limit} | Top: {top} | Generate: {generate_top}")
    if skip_llm:
        console.print("[yellow]LLM calls skipped — scoring only[/yellow]")

    packages = asyncio.run(
        run_pipeline(
            niche_list,
            limit=limit,
            top_n=top,
            generate_top=generate_top,
            style=style,
            platform=platform,
            output_dir=output,
            llm_provider=llm_provider,
            skip_llm=skip_llm,
            db_path=db_path,
        )
    )

    if packages:
        table = Table(title="Generated Packages")
        table.add_column("#", style="dim")
        table.add_column("Score", justify="right")
        table.add_column("Title", max_width=50)
        table.add_column("Niche")
        table.add_column("Has Lyrics")
        for i, pkg in enumerate(packages, 1):
            table.add_row(
                str(i),
                f"{pkg.score.final_score:.3f}",
                pkg.tutorial.title[:50],
                pkg.tutorial.niche.value,
                "Yes" if pkg.lyrics.full_text else "No",
            )
        console.print(table)
    else:
        console.print("[yellow]No packages generated — check API keys[/yellow]")


@cli.command()
@click.option("--format", "-f", "fmt", default="md", help="Output format: md or json")
@click.option("--run-id", default="", help="Specific run ID (latest if empty)")
@click.option("--output", "-o", default="./output", help="Output directory")
@click.option("--db-path", default="./trendbot.db", help="SQLite database path")
def report(fmt: str, run_id: str, output: str, db_path: str) -> None:
    """Generate a report from stored data."""
    from trendbot.models import TutorialPackage
    from trendbot.reporting import save_report
    from trendbot.storage.db import TrendBotDB

    db = TrendBotDB(db_path)
    runs = db.get_runs(limit=1)
    if not runs:
        console.print("[red]No runs found in database[/red]")
        return

    target_run = run_id or runs[0].run_id
    console.print(f"[bold]Generating report for run {target_run}[/bold]")

    packages: list[TutorialPackage] = []
    tutorials = db.get_tutorials_for_run(target_run, limit=50)
    for row in tutorials:
        pkg_json = db.get_package(row["fingerprint"], target_run)
        if pkg_json:
            packages.append(TutorialPackage.model_validate_json(pkg_json))

    if not packages:
        console.print("[yellow]No packages found for this run[/yellow]")
        return

    files = save_report(packages, run_id=target_run, output_dir=output, formats=[fmt])
    for f in files:
        console.print(f"[green]Report saved: {f}[/green]")
    db.close()


@cli.command()
@click.option("--output", "-o", default="./output/charts", help="Chart output directory")
@click.option("--db-path", default="./trendbot.db", help="SQLite database path")
def charts(output: str, db_path: str) -> None:
    """Generate PNG charts from stored data."""
    from trendbot.charts import generate_charts

    console.print("[bold]Generating charts...[/bold]")
    files = generate_charts(db_path=db_path, output_dir=output)
    if files:
        for f in files:
            console.print(f"[green]Chart saved: {f}[/green]")
    else:
        console.print("[yellow]No charts generated (need at least one run in DB)[/yellow]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
