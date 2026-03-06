# AutonoCX - Autonomous Enterprise Support Agent Platform

## Project Overview
Enterprise AI agent platform that autonomously handles customer support across voice, chat, and email with backend action execution and human-in-the-loop governance.

## Tech Stack
- **Frontend**: React 19 + Vite + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python 3.13) with async SQLAlchemy
- **Database**: PostgreSQL 16 + pgvector for RAG
- **Cache**: Redis 7
- **AI**: Multi-LLM (OpenAI, Anthropic) with tool calling
- **Package Management**: pnpm (frontend), uv (backend)
- **Monorepo**: pnpm workspaces

## Project Structure
```
packages/
  frontend/     # React dashboard app (port 5173)
  backend/      # FastAPI API server (port 8000)
  widget/       # Embeddable chat widget (IIFE build)
  shared/       # Shared TypeScript types/utils
infra/
  docker/       # docker-compose, Dockerfiles, nginx
scripts/        # setup.sh, migrate.sh, seed.sh
```

## Development Commands

### Setup
```bash
./scripts/setup.sh              # First-time setup
cp .env.example .env            # Then edit .env with your API keys
```

### Backend
```bash
cd packages/backend
uv sync                         # Install Python dependencies
uv run uvicorn autonomocx.main:app --reload --port 8000
uv run pytest                   # Run tests
uv run ruff check src/          # Lint
uv run alembic upgrade head     # Run migrations
uv run alembic revision --autogenerate -m "description"  # Create migration
```

### Frontend
```bash
cd packages/frontend
pnpm install                    # Install deps
pnpm dev                        # Dev server on :5173
pnpm build                      # Production build
pnpm lint                       # Lint
```

### Docker
```bash
pnpm docker:up                  # Start postgres + redis + backend + frontend
pnpm docker:down                # Stop all services
pnpm docker:logs                # View logs
```

## Architecture

### Backend Module Organization
- `core/` — Config, database, redis, security, dependencies, exceptions
- `middleware/` — Auth, CORS, rate limiting, request ID, org context, PII filter
- `models/` — SQLAlchemy ORM models (20 tables)
- `schemas/` — Pydantic request/response schemas
- `api/v1/` — FastAPI routers (REST + WebSocket)
- `services/` — Business logic layer
- `ai/` — Agent intelligence (orchestrator, LLM router, RAG, tools, guardrails)
- `channels/` — Omnichannel adapters (webchat, whatsapp, email, voice, sms)
- `workers/` — Background task processors

### AI Pipeline Flow
1. Customer message → Orchestrator
2. Context assembly (session memory + long-term memory + conversation history)
3. Intent classification + sentiment detection
4. RAG retrieval from knowledge base (pgvector)
5. LLM reasoning with tool planning
6. Guardrail checks (risk scoring, PII, hallucination)
7. Tool execution with HITL gating
8. Response delivery + audit logging

### API Base URL
- Backend: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

## Conventions
- Python: ruff for linting, 100 char line length, async/await everywhere
- TypeScript: ESLint + Prettier, Zustand for state, Axios for API calls
- Database: Alembic migrations, UUID primary keys, JSONB for flexible data
- API: RESTful, versioned (/api/v1), JWT auth, role-based access control
- All timestamps in UTC with timezone

## Agent Workflow
- **Push after implementation**: After completing any feature/fix/module, push to GitHub immediately
- In all interactions and commit messages, be extremely concise; sacrifice grammar for concision

## Code Quality Standards
- Make minimal, surgical changes
- **Never compromise type safety**: No `any`, no non-null assertion operator (`!`), no type assertions (`as Type`)
- **Make illegal states unrepresentable**: Model domain with ADTs/discriminated unions; parse inputs at boundaries into typed structures; if state can't exist, code can't mishandle it
- **Abstractions**: Consciously constrained, pragmatically parameterised, doggedly documented

### ENTROPY REMINDER
This codebase will outlive you. Every shortcut you take becomes
someone else's burden. Every hack compounds into technical debt
that slows the whole team down.
You are not just writing code. You are shaping the future of this
project. The patterns you establish will be copied. The corners
you cut will be cut again.
**Fight entropy. Leave the codebase better than you found it.**

## Testing
- Write tests that verify semantically correct behavior
- **Failing tests are acceptable** when they expose genuine bugs and test correct behavior

## Git, VCS, Pull Requests, Commits
- **ALWAYS check for `.jj/` dir before ANY VCS command** — if present, use jj not git
- **Never** add Claude to attribution or as a contributor in PRs, commits, messages, or PR descriptions
- **gh CLI available** for GitHub operations (PRs, issues, etc.)
- **glab CLI available** for GitLab operations (PRs, issues, etc.)

## Plans
- At end of each plan, give list of unresolved questions. Make questions extremely concise. Sacrifice grammar for concision.

## Specialized Subagents
### Oracle
Invoke for: code review, architecture decisions, debugging analysis, refactor planning, second opinion.
### Librarian
Invoke for: understanding 3rd party libraries/packages, exploring remote repos, discovering open source patterns.
### Overseer
Invoke for: task orchestration, milestone/task/subtask management, finding next ready work, recording learnings, tracking multi-session work.
