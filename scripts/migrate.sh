#!/usr/bin/env bash
# ============================================================
# AutonoCX -- Run Alembic database migrations
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/packages/backend"

echo "[migrate] Running Alembic migrations..."
cd "$BACKEND_DIR"
uv run alembic upgrade head

echo "[migrate] Done."
