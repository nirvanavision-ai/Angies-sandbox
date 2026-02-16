# CLAUDE.md — TrendBot

## Project Overview

TrendBot is a Python CLI and web application that discovers trending tutorials across multiple platforms, ranks them using a scoring engine, and converts top tutorials into viral song formats using LLM-powered content generation. It produces complete packages including lyrics, music specs, Suno/Udio prompts, and viral marketing materials.

## Tech Stack

- **Language:** Python 3.11+
- **Build system:** setuptools (via `pyproject.toml`)
- **CLI:** Click + Rich
- **Web UI:** FastAPI + Uvicorn
- **HTTP client:** httpx (async)
- **Data validation:** Pydantic v2
- **LLM clients:** Anthropic (Claude), OpenAI (GPT)
- **Storage:** SQLite (via stdlib `sqlite3`)
- **Visualization:** matplotlib
- **Linter/Formatter:** Ruff
- **Testing:** pytest + pytest-asyncio + pytest-cov

## Repository Structure

```
src/trendbot/
├── __init__.py
├── __main__.py            # CLI entry point (python -m trendbot)
├── cli.py                 # Click command definitions
├── models.py              # Pydantic models, enums, URL utilities
├── llm.py                 # Pluggable LLM abstraction (Anthropic/OpenAI/Mock)
├── pipeline.py            # 4-phase orchestration (discover→rank→generate→report)
├── reporting.py           # Markdown + JSON report generation
├── charts.py              # matplotlib chart generation
├── providers/
│   ├── base.py            # BaseProvider abstract class
│   ├── registry.py        # Provider discovery & concurrent fan-out
│   ├── tavily.py          # Tavily web search
│   ├── serpapi.py         # SerpAPI/Google search
│   ├── youtube.py         # YouTube Data API v3
│   ├── reddit.py          # Reddit API + RSS fallback
│   ├── github.py          # GitHub trending repos
│   └── twitter.py         # X/Twitter (stub)
├── ranking/
│   ├── scorer.py          # Scoring engine (recency, engagement, authority, velocity)
│   └── niche_classifier.py # Keyword-based niche classification
├── critique/
│   ├── self_critique.py   # LLM-based trend validation
│   └── concept_engine.py  # Creative "WTF-genius" idea generation
├── lyricist/
│   └── songwriter.py      # Tutorial → song lyrics + music spec
├── prompts/
│   ├── suno.py            # Suno/Udio AI music prompt generation
│   └── viral_packaging.py # Titles, hooks, captions, hashtags
├── storage/
│   └── db.py              # SQLite persistence (runs, tutorials, packages)
├── ui/
│   └── app.py             # FastAPI web UI
└── utils/
    └── __init__.py

tests/
├── test_llm.py            # LLM JSON extraction
├── test_scoring.py        # Scoring engine
├── test_niche_classifier.py # Niche classification
├── test_dedupe.py         # URL normalization & deduplication
└── test_storage.py        # SQLite layer

examples/
├── example_output_ai_music.json  # Sample output package
└── example_output_ai_music.md    # Sample markdown report
```

## Common Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run all tests with coverage
pytest tests/ -v --cov=src/trendbot

# Run a specific test file
pytest tests/test_scoring.py -v

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Full end-to-end pipeline
python -m trendbot run --niches "ai,coding,ai_music" --limit 50 --generate-top 5

# Discovery only
python -m trendbot discover --niches "ai,finance" --limit 100

# Rank from saved JSON
python -m trendbot rank --input output/discovered.json --top 20

# Single URL generation
python -m trendbot generate --tutorial-url "https://youtube.com/watch?v=..." --style "hyperpop"

# Generate reports from DB
python -m trendbot report --format md

# Create charts
python -m trendbot charts

# Scoring only (skip LLM calls)
python -m trendbot run --niches "ai" --skip-llm

# Launch web UI
uvicorn trendbot.ui.app:app --reload --port 8000
```

## Architecture

### Pipeline Phases

1. **Discovery** — Queries 6+ providers concurrently via `asyncio.gather()` for each niche, classifies results, and deduplicates by content fingerprint.
2. **Ranking** — Scores tutorials on [0,1] using weighted formula: `base = 0.45*recency + 0.45*engagement + 0.10*authority`, plus trend velocity/acceleration bonuses and cross-platform bonuses.
3. **Generation** — Runs LLM-powered critique + concept generation in parallel, then sequentially: lyrics, music spec, Suno prompt, viral packaging.
4. **Reporting** — Saves markdown + JSON reports and stores snapshots in SQLite for week-over-week delta analysis.

### Provider Pattern

All providers extend `BaseProvider` (abstract class in `providers/base.py`):
- `search(query, limit) -> list[TutorialResult]` — Perform search
- `available() -> bool` — Check if credentials are configured
- Registry in `providers/registry.py` handles fan-out and error isolation

### LLM Abstraction

Pluggable clients in `llm.py`:
- `AnthropicClient` — Default model: `claude-sonnet-4-20250514`
- `OpenAIClient` — Default model: `gpt-4o`
- `MockLLMClient` — Deterministic responses for testing without API keys

Selection priority: `TRENDBOT_LLM_PROVIDER` env var > available API key (Anthropic preferred) > MockLLMClient.

### Data Models

Core models live in `models.py`:
- **Enums:** `Niche` (14 categories), `Platform` (9 platforms), `TrendType` (5 lifecycle stages)
- **Key models:** `TutorialResult`, `ScoreBreakdown`, `CritiqueResult`, `ConceptIdea`, `MusicSpec`, `LyricDraft`, `SunoPrompt`, `ViralPackaging`, `TutorialPackage`, `RunSnapshot`, `ScoringWeights`
- **Utilities:** `normalize_url()`, `extract_youtube_id()`, `content_fingerprint()`

## Code Conventions

- **Type hints** on all function signatures (Python 3.11+ style)
- **`from __future__ import annotations`** for forward references
- **Docstrings** on public functions
- **Named loggers** per module (`logger = logging.getLogger(__name__)`)
- **Line length:** 100 characters (configured in `[tool.ruff]`)
- **Target Python:** 3.11
- **Async-first:** Provider calls, LLM calls, and pipeline phases use `async`/`await`
- **Pydantic v2** for all data models with validation
- **Custom exceptions:** `ProviderError` for non-fatal provider failures; `ValueError` for JSON extraction failures
- **Modular package layout** under `src/trendbot/` with `__init__.py` in every directory

## Environment Configuration

Copy `.env.example` to `.env` and fill in API keys:

- **Required (at least one search provider):** `TAVILY_API_KEY`, `SERPAPI_API_KEY`
- **Required (at least one LLM):** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- **Optional:** `YOUTUBE_API_KEY`, `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`, `GITHUB_TOKEN`
- **Config:** `TRENDBOT_LLM_PROVIDER` (anthropic|openai), `TRENDBOT_DB_PATH`, `TRENDBOT_LOG_LEVEL`

Never commit `.env` — it is in `.gitignore`.

## Testing

- Tests live in `tests/` and cover scoring, LLM JSON extraction, niche classification, URL deduplication, and storage
- Async tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Storage tests use temporary SQLite files via fixtures
- Run `pytest tests/ -v --cov=src/trendbot` for full coverage report
- Tests do not require API keys — `MockLLMClient` and fixtures handle isolation

## Related Documents

- `README.md` — User-facing documentation and usage examples
- `FLOW-PROTOCOL-VISION.md` — Strategic vision for 10 culture-finance protocol concepts built on top of TrendBot's infrastructure
