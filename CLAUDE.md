# CLAUDE.md

## Project Overview

TrendBot is a Python async application that discovers trending tutorials across multiple platforms and converts them into viral "song tutorials" with lyrics, music specs, and AI music generation prompts.

## Tech Stack

- **Language**: Python 3.11+
- **Async**: asyncio throughout
- **CLI**: Click
- **Web UI**: FastAPI + Uvicorn + Jinja2
- **Data models**: Pydantic v2
- **HTTP**: httpx (async)
- **LLM providers**: Anthropic (Claude), OpenAI (GPT-4o)
- **Database**: SQLite
- **Charts**: Matplotlib
- **Linting/Formatting**: Ruff

## Repository Structure

```
src/trendbot/           # Main package
  cli.py                # Click CLI commands (discover, rank, generate, run, report, charts)
  pipeline.py           # Orchestration: discover -> rank -> generate -> report
  models.py             # Pydantic models (TutorialResult, ScoreBreakdown, LyricDraft, etc.)
  llm.py                # LLM abstraction (Anthropic, OpenAI, Mock clients)
  reporting.py          # Markdown + JSON report generation
  charts.py             # Matplotlib visualizations
  providers/            # Data source providers (tavily, serpapi, youtube, reddit, github, twitter)
  ranking/              # Scoring engine + niche classifier
  critique/             # LLM-based trend validation + concept generation
  lyricist/             # Tutorial -> song lyrics + music spec
  prompts/              # Suno/Udio prompt + viral packaging generation
  storage/              # SQLite persistence layer
  ui/                   # FastAPI web dashboard
tests/                  # pytest test suite
examples/               # Sample output reports (markdown + JSON)
```

## Common Commands

```bash
# Install (editable, with dev dependencies)
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Run end-to-end pipeline
python -m trendbot run --niches "ai,coding" --limit 50 --generate-top 5

# Discover tutorials only
python -m trendbot discover --niches "ai,coding,ai_music" --limit 100

# Start web UI
uvicorn trendbot.ui.app:app --reload
```

## Code Style

- **Line length**: 100 characters
- **Linter**: Ruff targeting Python 3.11
- **Async**: All I/O operations use async/await
- **Models**: Pydantic v2 for all data structures with validation
- **Providers**: Implement `BaseProvider.search()` interface in `providers/base.py`

## Testing

- Framework: pytest with pytest-asyncio (asyncio_mode = "auto")
- Test directory: `tests/`
- Tests cover: scoring, LLM clients, niche classification, storage, deduplication
- Run before committing: `pytest tests/ -v && ruff check src/ tests/`

## Environment Variables

Key API keys (see `.env.example` for full list):

- `ANTHROPIC_API_KEY` - Claude LLM (recommended)
- `OPENAI_API_KEY` - GPT alternative
- `TAVILY_API_KEY` - Web search
- `SERPAPI_API_KEY` - Google search
- `YOUTUBE_API_KEY` - Video metadata
- `TRENDBOT_LLM_PROVIDER` - "anthropic" or "openai"
- `TRENDBOT_DB_PATH` - SQLite path (default: ./trendbot.db)

## Architecture Notes

- Pipeline flow: Discovery (providers) -> Ranking (scorer) -> Generation (critique + lyricist + prompts) -> Reporting
- Providers run concurrently via asyncio; results are deduplicated by content fingerprint (SHA256 of title + canonical URL)
- Scoring formula: 45% recency (7-day half-life decay) + 45% engagement (log-normalized) + 10% authority, plus trend velocity and cross-platform bonuses
- LLM calls are abstracted behind `LLMClient` base class; `MockLLMClient` enables offline testing
