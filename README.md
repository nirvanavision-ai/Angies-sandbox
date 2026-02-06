# TrendBot — Tutorial Discovery + Song Converter

Discover trending tutorials across niches (AI, coding, finance, etc.) and convert them into viral "song tutorials" with lyrics, music specs, and Suno/Udio prompts.

## Architecture

```
src/trendbot/
  models.py         — Pydantic data models, URL normalization, dedup
  llm.py            — LLM abstraction (Anthropic / OpenAI / Mock)
  pipeline.py       — Main orchestration: discover → rank → generate → report
  cli.py            — Click CLI with all commands
  reporting.py      — Markdown + JSON report generation
  charts.py         — matplotlib chart generation from SQLite data
  providers/
    base.py          — BaseProvider interface
    tavily.py        — Tavily web search
    serpapi.py       — SerpAPI / Google search
    youtube.py       — YouTube Data API v3
    reddit.py        — Reddit API + RSS fallback
    github.py        — GitHub trending repos
    twitter.py       — X/Twitter stub
    registry.py      — Provider discovery + concurrent fan-out
  ranking/
    scorer.py        — Scoring engine (recency + engagement + authority + velocity)
    niche_classifier.py — Keyword-based niche classification
  critique/
    self_critique.py — LLM-powered trend validation
    concept_engine.py — "WTF" creative concept generation
  lyricist/
    songwriter.py    — Tutorial → song lyrics + music spec
  prompts/
    suno.py          — Suno/Udio prompt generation
    viral_packaging.py — Titles, hooks, captions, hashtags
  storage/
    db.py            — SQLite persistence (runs, tutorials, packages, deltas)
  ui/
    app.py           — FastAPI web UI
```

## Setup

```bash
# Clone and install
git clone <repo-url> && cd trendbot
pip install -e ".[dev]"

# Copy and fill in your API keys
cp .env.example .env
# Edit .env with your keys
```

### Required API Keys

| Key | Required | Purpose |
|-----|----------|---------|
| `TAVILY_API_KEY` | At least one search | Web discovery |
| `SERPAPI_API_KEY` | At least one search | Google search results |
| `YOUTUBE_API_KEY` | Optional | Video metadata, view counts |
| `ANTHROPIC_API_KEY` | At least one LLM | Lyrics, concepts, critique |
| `OPENAI_API_KEY` | At least one LLM | Alternative LLM provider |
| `REDDIT_CLIENT_ID` / `SECRET` | Optional | Reddit discussions |
| `GITHUB_TOKEN` | Optional | Higher rate limits |

## CLI Commands

### End-to-end run
```bash
python -m trendbot run --niches "ai,coding,ai_music" --limit 50 --generate-top 5
```

### Discover only
```bash
python -m trendbot discover --niches "ai,finance,graphic_design" --limit 100
```

### Rank from file
```bash
python -m trendbot rank --input output/discovered.json --top 20
```

### Generate song for a single URL
```bash
python -m trendbot generate --tutorial-url "https://youtube.com/watch?v=..." --style "hyperpop"
```

### Generate report from DB
```bash
python -m trendbot report --format md
```

### Generate charts
```bash
python -m trendbot charts
```

### Skip LLM calls (scoring only)
```bash
python -m trendbot run --niches "ai" --skip-llm
```

## Web UI

```bash
uvicorn trendbot.ui.app:app --reload --port 8000
# Open http://localhost:8000
```

## Scoring Model

```
base_score = 0.45 * recency + 0.45 * engagement + 0.10 * authority
trend_bonus = f(velocity, acceleration)  — fast risers get boosted
cross_platform_bonus = 0.15 * (n_platforms - 1)
final_score = min(1.0, base_score + trend_bonus + cross_platform_bonus)
```

Configurable via `ScoringWeights` model. Recency uses exponential decay with 7-day half-life. Engagement uses log-scale normalization to prevent outlier dominance.

## Adding New Providers

1. Create `src/trendbot/providers/my_provider.py`
2. Subclass `BaseProvider`:
   ```python
   class MyProvider(BaseProvider):
       name = "my_provider"
       def available(self) -> bool: ...
       async def search(self, query, *, limit=20) -> list[TutorialResult]: ...
   ```
3. Add to `ALL_PROVIDERS` in `registry.py`

## Tuning Scoring

Pass custom weights to the pipeline:
```python
from trendbot.models import ScoringWeights
weights = ScoringWeights(recency=0.6, engagement=0.3, authority=0.1)
```

## Tuning Lyrics

- Edit prompts in `src/trendbot/lyricist/songwriter.py`
- Change `_SYSTEM` for personality / tone
- Change `_LYRICS_PROMPT` for structure / format

## Tests

```bash
pytest tests/ -v
```

## Output

Reports are saved to `./output/` as both Markdown and JSON. Charts go to `./output/charts/`.

## License

MIT
