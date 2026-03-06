# ============================================================
# AutonoCX Frontend - Development Dockerfile
# ============================================================

FROM node:22-alpine

# Enable pnpm via corepack
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy dependency files first for layer caching
COPY package.json ./
COPY pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

# Copy application source
COPY . .

EXPOSE 5173

# Default command: start the Vite dev server
CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "5173"]
