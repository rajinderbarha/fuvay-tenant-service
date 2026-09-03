-- Fuvay — Postgres initialization
-- Runs once when the container first starts.

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";          -- pgvector for RAG engine

-- Platform schema (all shared tables live here)
CREATE SCHEMA IF NOT EXISTS public;

-- Verify
SELECT extname, extversion FROM pg_extension
WHERE extname IN ('uuid-ossp', 'pgcrypto', 'vector');
