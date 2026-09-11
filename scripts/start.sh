#!/usr/bin/env bash
# Start LandLekha for a demo on Linux/macOS: API on :8000, UI on :5173.
#   scripts/start.sh            dev UI (hot reload)
#   scripts/start.sh --built    single port, built UI at :8000
#   scripts/start.sh --fresh    wipe storage/ first (empty database for a clean demo)
set -euo pipefail
cd "$(dirname "$0")/.."

built=0
for arg in "$@"; do
  case "$arg" in
    --built) built=1 ;;
    --fresh) rm -rf storage && echo "storage/ cleared" ;;
  esac
done

if [ "$built" = 1 ]; then
  (cd frontend && { [ -d node_modules ] || npm install; } && npm run build)
  echo "LandLekha at http://localhost:8000  (API docs: /docs)"
  exec python -m uvicorn backend.api.main:app --port 8000
fi

python -m uvicorn backend.api.main:app --port 8000 &
api=$!
trap 'kill $api 2>/dev/null' EXIT
cd frontend
[ -d node_modules ] || npm install
echo "UI at http://localhost:5173   API docs at http://localhost:8000/docs"
npm run dev
