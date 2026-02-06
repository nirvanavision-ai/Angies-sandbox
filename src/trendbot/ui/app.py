"""Minimal FastAPI web UI for TrendBot."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from trendbot.models import ScoringWeights, TutorialPackage
from trendbot.pipeline import discover, generate_single, rank, run_pipeline
from trendbot.storage.db import TrendBotDB

app = FastAPI(title="TrendBot", version="0.1.0")

DB_PATH = os.environ.get("TRENDBOT_DB_PATH", "./trendbot.db")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrendBot — Tutorial Song Discovery</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #0f0f1a; color: #e0e0e0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #8b5cf6; font-size: 2rem; margin-bottom: 8px; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px;
                margin-bottom: 16px; border: 1px solid #2a2a4a; }
        .card:hover { border-color: #8b5cf6; }
        .card h3 { color: #c084fc; margin-bottom: 8px; }
        .meta { color: #888; font-size: 0.85rem; margin-bottom: 8px; }
        .score-bar { height: 6px; background: #2a2a4a; border-radius: 3px;
                     margin: 8px 0; overflow: hidden; }
        .score-fill { height: 100%; background: linear-gradient(90deg, #8b5cf6, #ec4899);
                      border-radius: 3px; transition: width 0.5s; }
        .tag { display: inline-block; background: #2a2a4a; color: #c084fc;
               padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; margin: 2px; }
        .form-group { margin-bottom: 16px; }
        label { display: block; color: #888; margin-bottom: 4px; font-size: 0.85rem; }
        input, select { width: 100%; padding: 10px; background: #2a2a4a; border: 1px solid #3a3a5a;
                        border-radius: 8px; color: #e0e0e0; font-size: 0.9rem; }
        input:focus, select:focus { outline: none; border-color: #8b5cf6; }
        button { background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white;
                 border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer;
                 font-size: 1rem; font-weight: 600; }
        button:hover { opacity: 0.9; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .section { margin-top: 30px; }
        .lyrics-box { background: #12121f; padding: 16px; border-radius: 8px;
                      font-family: monospace; white-space: pre-wrap; font-size: 0.85rem;
                      max-height: 400px; overflow-y: auto; }
        .status { padding: 12px; border-radius: 8px; margin: 12px 0; }
        .status.loading { background: #1a1a3e; border: 1px solid #3b3b6d; }
        .status.success { background: #0a2a1a; border: 1px solid #1a5a3a; }
        .status.error { background: #2a0a0a; border: 1px solid #5a1a1a; }
        #results { margin-top: 20px; }
        a { color: #8b5cf6; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>TrendBot</h1>
        <p class="subtitle">Discover trending tutorials. Turn them into viral songs.</p>

        <div class="grid">
            <div class="card">
                <h3>Quick Run</h3>
                <div class="form-group">
                    <label>Niches (comma-separated)</label>
                    <input type="text" id="niches" value="ai,coding,ai_music" />
                </div>
                <div class="form-group">
                    <label>Max results</label>
                    <input type="number" id="limit" value="20" min="5" max="200" />
                </div>
                <div class="form-group">
                    <label>Generate top N</label>
                    <input type="number" id="gen_top" value="3" min="1" max="20" />
                </div>
                <button onclick="runPipeline()">Discover & Generate</button>
            </div>

            <div class="card">
                <h3>Single URL</h3>
                <div class="form-group">
                    <label>Tutorial URL</label>
                    <input type="url" id="url" placeholder="https://youtube.com/watch?v=..." />
                </div>
                <div class="form-group">
                    <label>Musical style</label>
                    <input type="text" id="style" placeholder="hyperpop, lo-fi, jazz..." />
                </div>
                <button onclick="generateSingle()">Generate Song</button>
            </div>
        </div>

        <div id="status"></div>
        <div id="results"></div>
    </div>

    <script>
        function setStatus(msg, type) {
            document.getElementById('status').innerHTML =
                `<div class="status ${type}">${msg}</div>`;
        }

        async function runPipeline() {
            const niches = document.getElementById('niches').value;
            const limit = document.getElementById('limit').value;
            const gen_top = document.getElementById('gen_top').value;
            setStatus('Running pipeline... this may take a minute.', 'loading');

            try {
                const resp = await fetch('/api/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({niches, limit: parseInt(limit), generate_top: parseInt(gen_top)})
                });
                const data = await resp.json();
                if (data.error) { setStatus(data.error, 'error'); return; }
                setStatus(`Found ${data.packages.length} packages!`, 'success');
                renderPackages(data.packages);
            } catch(e) { setStatus('Error: ' + e.message, 'error'); }
        }

        async function generateSingle() {
            const url = document.getElementById('url').value;
            const style = document.getElementById('style').value;
            if (!url) { setStatus('Please enter a URL', 'error'); return; }
            setStatus('Generating song tutorial...', 'loading');

            try {
                const resp = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url, style})
                });
                const data = await resp.json();
                if (data.error) { setStatus(data.error, 'error'); return; }
                setStatus('Song generated!', 'success');
                renderPackages([data.package]);
            } catch(e) { setStatus('Error: ' + e.message, 'error'); }
        }

        function renderPackages(pkgs) {
            let html = '<div class="section"><h2 style="color:#8b5cf6;margin-bottom:16px">Results</h2>';
            pkgs.forEach((pkg, i) => {
                const t = pkg.tutorial;
                const s = pkg.score;
                html += `<div class="card">
                    <h3>${i+1}. ${t.title}</h3>
                    <div class="meta">
                        <span class="tag">${t.platform}</span>
                        <span class="tag">${t.niche}</span>
                        <a href="${t.url}" target="_blank">View tutorial</a>
                    </div>
                    <div class="score-bar"><div class="score-fill" style="width:${s.final_score*100}%"></div></div>
                    <div class="meta">Score: ${s.final_score.toFixed(3)} (R:${s.recency.toFixed(2)} E:${s.engagement.toFixed(2)} A:${s.authority.toFixed(2)})</div>`;

                if (pkg.why_trending) html += `<p style="margin:8px 0"><b>Why trending:</b> ${pkg.why_trending}</p>`;

                if (pkg.concepts && pkg.concepts.length > 0) {
                    html += '<div style="margin:8px 0"><b>Concepts:</b><ul>';
                    pkg.concepts.forEach(c => { html += `<li><b>${c.hook}</b> — ${c.angle}</li>`; });
                    html += '</ul></div>';
                }

                if (pkg.lyrics && pkg.lyrics.full_text) {
                    html += `<details><summary style="cursor:pointer;color:#c084fc">Show Lyrics</summary>
                        <div class="lyrics-box">${pkg.lyrics.full_text}</div></details>`;
                }

                if (pkg.suno_prompt && pkg.suno_prompt.style_prompt) {
                    html += `<details><summary style="cursor:pointer;color:#c084fc">Suno Prompt</summary>
                        <div class="lyrics-box"><b>Style:</b> ${pkg.suno_prompt.style_prompt}
<b>Negative:</b> ${pkg.suno_prompt.negative_prompt || 'none'}

<b>Short version:</b>
${pkg.suno_prompt.short_version_lyrics || 'N/A'}

<b>Full version:</b>
${pkg.suno_prompt.full_version_lyrics || 'N/A'}</div></details>`;
                }

                if (pkg.viral_packaging && pkg.viral_packaging.suggested_title) {
                    const vp = pkg.viral_packaging;
                    html += `<details><summary style="cursor:pointer;color:#c084fc">Viral Packaging</summary>
                        <div class="lyrics-box"><b>Title:</b> ${vp.suggested_title}
<b>10s Hook:</b> ${vp.ten_second_hook_script}
<b>TikTok:</b> ${vp.tiktok_caption}
<b>Hashtags:</b> ${(vp.hashtags || []).join(' ')}</div></details>`;
                }

                html += '</div>';
            });
            html += '</div>';
            document.getElementById('results').innerHTML = html;
        }
    </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE


@app.post("/api/run")
async def api_run(request: Request):
    try:
        body = await request.json()
        niches = [n.strip() for n in body.get("niches", "ai").split(",")]
        limit = body.get("limit", 20)
        generate_top = body.get("generate_top", 3)

        packages = await run_pipeline(
            niches,
            limit=limit,
            top_n=min(limit, 50),
            generate_top=generate_top,
            db_path=DB_PATH,
        )
        return JSONResponse({
            "packages": [p.model_dump(mode="json") for p in packages],
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/generate")
async def api_generate(request: Request):
    try:
        body = await request.json()
        url = body.get("url", "")
        style = body.get("style", "")
        if not url:
            return JSONResponse({"error": "URL required"}, status_code=400)

        pkg = await generate_single(url, style=style)
        return JSONResponse({
            "package": pkg.model_dump(mode="json"),
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/runs")
async def api_runs():
    db = TrendBotDB(DB_PATH)
    runs = db.get_runs(limit=20)
    db.close()
    return JSONResponse({
        "runs": [r.model_dump(mode="json") for r in runs],
    })


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
