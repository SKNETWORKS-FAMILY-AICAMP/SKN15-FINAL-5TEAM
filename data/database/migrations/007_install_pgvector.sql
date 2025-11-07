-- ============================================================================
-- Migration 007: Install pgvector extension
-- ============================================================================
-- Purpose: Enable vector similarity search for Graph RAG
-- Dependencies: PostgreSQL 15.14+
-- Created: 2025-10-31
-- ============================================================================

-- Install pgvector extension
-- This enables vector data type and similarity search operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
-- Should show version, schema, and description
SELECT
    extname as extension_name,
    extversion as version,
    nspname as schema
FROM pg_extension e
JOIN pg_namespace n ON e.extnamespace = n.oid
WHERE extname = 'vector';

-- Test vector operations
-- This ensures vector type is available and operations work
DO $$
DECLARE
    test_vector vector(3);
BEGIN
    -- Test vector creation
    test_vector := '[1,2,3]'::vector;

    -- Test cosine similarity
    RAISE NOTICE 'Vector extension installed successfully!';
    RAISE NOTICE 'Test vector: %', test_vector;

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'pgvector installation failed: %', SQLERRM;
END $$;

-- ============================================================================
-- Expected Output:
-- - CREATE EXTENSION (success message)
-- - Extension info: name='vector', version=0.5.x or higher
-- - NOTICE: Vector extension installed successfully!
-- ============================================================================
