-- ============================================================
-- AutonoCX: PostgreSQL initialization script
-- Runs once when the container is created for the first time.
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for embedding storage and similarity search
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable pgcrypto for gen_random_uuid() and cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
