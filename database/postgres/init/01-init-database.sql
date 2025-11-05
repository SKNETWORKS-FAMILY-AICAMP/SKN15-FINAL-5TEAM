-- KIME Chat PostgreSQL Initialization Script
-- This script runs automatically when the PostgreSQL container is first created

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS statedb;
CREATE SCHEMA IF NOT EXISTS public;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA statedb TO kime;
GRANT ALL PRIVILEGES ON SCHEMA public TO kime;

-- Set search path
ALTER DATABASE kimedb SET search_path TO statedb, public;

\echo 'PostgreSQL initialization completed successfully'
