#!/usr/bin/env bash
# Run the app on this machine, settings from .env.
{{#frontend}}
#   scripts/run-local.sh          # build the frontend, serve everything on PORT ({{port}})
#   scripts/run-local.sh --dev    # Vite with hot reload on http://localhost:5173 (proxies /api to the backend)
{{/frontend}}
{{^frontend}}
#   scripts/run-local.sh          # serve the API on PORT ({{port}})
{{/frontend}}
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
source scripts/lib.sh

dev=""
case "${1:-}" in
  "") ;;
  --dev) dev=1 ;;
  *) echo "usage: $0 [--dev]" >&2; exit 1 ;;
esac

need uv "https://docs.astral.sh/uv/getting-started/installation/"
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example."; }
uv sync
# fail now, not after the build, when another app holds the port
port=$(uv run python -c "from {{pkg}}.config import get_settings; print(get_settings().port)")
if (echo >"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
  holder=$(ss -ltnpH "sport = :$port" 2>/dev/null | grep -o 'users:(([^)]*' | head -1)
  echo "Port $port is in use${holder:+ ($holder)}: stop that, or set PORT in .env." >&2
  exit 1
fi
export PORT="$port"  # for Vite's proxy (--dev)
{{#db}}
scripts/db.sh up
{{/db}}
{{#frontend}}

need npm "https://nodejs.org"
[ -d frontend/node_modules ] || (cd frontend && npm ci)
if [ -n "$dev" ]; then
  (cd frontend && npm run dev) &
  trap 'kill $! 2>/dev/null || true' EXIT
else
  (cd frontend && npm run build)
fi
{{/frontend}}
{{^frontend}}
[ -z "$dev" ] || echo "--dev only matters with a frontend" >&2
{{/frontend}}
uv run {{app}}
