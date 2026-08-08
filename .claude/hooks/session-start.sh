#!/bin/bash
set -euo pipefail

# Only run in Claude Code on the web (remote sessions)
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Project dependencies (idempotent; pip skips already-satisfied requirements)
pip install -e ".[dev]"

# Youka CLI for karaoke/video generation.
# Tolerate failure: the environment's network policy may block api.youka.io,
# and YOUKA_API_KEY may not be configured as an environment secret yet.
if npm install -g @youka/cli; then
  if [ -n "${YOUKA_API_KEY:-}" ]; then
    if youka login "$YOUKA_API_KEY"; then
      echo "youka: authenticated"
    else
      echo "youka: login failed (network policy may block api.youka.io) — continuing without it" >&2
    fi
  else
    echo "youka: YOUKA_API_KEY not set — skipping login" >&2
  fi
else
  echo "youka: install failed — continuing without it" >&2
fi
