# ============================================================
# AutonoCX Backend - Multi-stage Dockerfile
# ============================================================

# -- Stage 1: Builder ------------------------------------------------
FROM python:3.13-slim AS builder

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies (without dev extras) into a virtual env
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

# -- Stage 2: Runtime ------------------------------------------------
FROM python:3.13-slim AS runtime

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv in runtime as well (needed for `uv run`)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/uv.lock* /app/

# Copy application source
COPY src/ /app/src/
COPY alembic/ /app/alembic/

# Ensure the virtual env is on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Default command: run with uvicorn
CMD ["uv", "run", "uvicorn", "autonomocx.main:app", "--host", "0.0.0.0", "--port", "8000"]
