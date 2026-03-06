#!/usr/bin/env bash
# ============================================================
# AutonoCX -- First-time local development setup
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker/docker-compose.yml"

# ── Colours ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ── 1. Check prerequisites ────────────────────────────────────
info "Checking prerequisites..."

check_command() {
    if ! command -v "$1" &>/dev/null; then
        fail "'$1' is not installed. Please install it and try again."
    fi
    ok "$1 found: $(command -v "$1")"
}

check_command docker
check_command node
check_command pnpm
check_command uv
check_command python3

# Verify Docker daemon is running
if ! docker info &>/dev/null; then
    fail "Docker daemon is not running. Please start Docker and try again."
fi
ok "Docker daemon is running"

# ── 2. Copy .env.example -> .env ──────────────────────────────
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        ok "Created .env from .env.example"
        warn "Please review $ENV_FILE and update secrets before going to production."
    else
        fail ".env.example not found at $ENV_EXAMPLE"
    fi
else
    ok ".env already exists -- skipping copy"
fi

# ── 3. Start infrastructure containers ────────────────────────
info "Starting PostgreSQL and Redis..."
docker compose -f "$COMPOSE_FILE" up -d postgres redis

# ── 4. Wait for PostgreSQL readiness ──────────────────────────
info "Waiting for PostgreSQL to become ready..."
MAX_RETRIES=30
RETRY=0
until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U autonomocx -d autonomocx &>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        fail "PostgreSQL did not become ready in time."
    fi
    sleep 1
done
ok "PostgreSQL is ready"

# ── 5. Install backend dependencies ──────────────────────────
info "Installing backend Python dependencies..."
cd "$ROOT_DIR/packages/backend"
uv sync --all-extras
ok "Backend dependencies installed"

# ── 6. Run database migrations ────────────────────────────────
info "Running Alembic migrations..."
cd "$ROOT_DIR/packages/backend"
uv run alembic upgrade head 2>/dev/null && ok "Migrations applied" || warn "No migrations to apply (or Alembic not yet initialised)"

# ── 7. Install frontend dependencies ─────────────────────────
info "Installing frontend dependencies..."
cd "$ROOT_DIR/packages/frontend"
pnpm install
ok "Frontend dependencies installed"

# ── 8. Done ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  AutonoCX development environment is ready!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  Backend API:    ${CYAN}http://localhost:8000${NC}"
echo -e "  API docs:       ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  Frontend:       ${CYAN}http://localhost:5173${NC}"
echo -e "  PostgreSQL:     ${CYAN}localhost:5432${NC}  (user: autonomocx)"
echo -e "  Redis:          ${CYAN}localhost:6379${NC}"
echo ""
echo -e "  Start backend:  ${YELLOW}cd packages/backend && uv run uvicorn autonomocx.main:app --reload${NC}"
echo -e "  Start frontend: ${YELLOW}cd packages/frontend && pnpm dev${NC}"
echo -e "  Run all:        ${YELLOW}docker compose -f infra/docker/docker-compose.yml up${NC}"
echo ""
