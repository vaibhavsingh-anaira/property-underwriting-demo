#!/usr/bin/env bash
# Start the Anaira showcase: API on :8765, web on :5173.
set -e
cd "$(dirname "$0")"
( cd backend && uv sync -q && [ -f ../data/world/events.json ] || PYTHONPATH=. uv run python -m uwc.generate )
( cd web && [ -d node_modules ] || npm install )
( cd backend && PYTHONPATH=. uv run uvicorn uwc.api:app --port 8765 ) &
API=$!
trap 'kill $API 2>/dev/null' EXIT
cd web && npx vite --port 5173
