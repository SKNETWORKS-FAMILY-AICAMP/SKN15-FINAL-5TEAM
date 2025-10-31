-- ============================================================================
-- Migration 008: Graph RAG Schema
-- ============================================================================
-- Purpose: Create tables and indexes for Graph RAG functionality
-- Dependencies: 007_install_pgvector.sql
-- Created: 2025-10-31
-- ============================================================================

-- Create schema for Graph RAG entities if not exists
-- We'll use statedb schema to keep graph data with session state
SET search_path TO statedb, public;

-- ============================================================================
-- Table 1: entities
-- ============================================================================
-- Stores all extracted entities (characters, locations, events, items, skills)
CREATE TABLE IF NOT EXISTS statedb.entities (
    entity_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- 'character', 'location', 'event', 'item', 'skill'
    entity_name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255),       -- Normalized name for deduplication
    description TEXT,
    properties JSONB DEFAULT '{}',     -- Flexible storage for entity-specific data
    embedding vector(1536),            -- OpenAI text-embedding-3-small (1536 dims)
    importance_score FLOAT DEFAULT 0.5, -- 0.0-1.0, for ranking
    community_id INTEGER,              -- For graph community detection
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_updated_at TIMESTAMP DEFAULT NOW(),
    mention_count INTEGER DEFAULT 0,   -- How often this entity appears
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_entity_type CHECK (entity_type IN ('character', 'location', 'event', 'item', 'skill')),
    CONSTRAINT valid_importance CHECK (importance_score >= 0.0 AND importance_score <= 1.0),
    UNIQUE (entity_type, canonical_name)
);

COMMENT ON TABLE statedb.entities IS 'Graph RAG entity storage with embeddings for semantic search';
COMMENT ON COLUMN statedb.entities.canonical_name IS 'Normalized name for deduplication (e.g., "렌고쿠" = "렌고쿠 쿄쥬로")';
COMMENT ON COLUMN statedb.entities.embedding IS 'Vector embedding for semantic similarity search (1536 dimensions)';
COMMENT ON COLUMN statedb.entities.importance_score IS 'Entity importance for ranking (0.0 = low, 1.0 = high)';
COMMENT ON COLUMN statedb.entities.community_id IS 'Graph community ID for clustering related entities';

-- ============================================================================
-- Table 2: entity_relationships
-- ============================================================================
-- Stores relationships between entities in the graph
CREATE TABLE IF NOT EXISTS statedb.entity_relationships (
    relationship_id SERIAL PRIMARY KEY,
    source_entity_id INTEGER NOT NULL REFERENCES statedb.entities(entity_id) ON DELETE CASCADE,
    target_entity_id INTEGER NOT NULL REFERENCES statedb.entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,  -- 'TRAINS_WITH', 'HAS_AFFINITY', 'OCCURRED_IN', etc.
    strength FLOAT DEFAULT 0.5,               -- 0.0-1.0, relationship strength
    confidence FLOAT DEFAULT 0.5,             -- 0.0-1.0, how confident we are
    properties JSONB DEFAULT '{}',            -- Relationship-specific metadata
    evidence_count INTEGER DEFAULT 1,         -- How many times observed
    first_observed_at TIMESTAMP DEFAULT NOW(),
    last_observed_at TIMESTAMP DEFAULT NOW(),
    provenance TEXT,                          -- Where this relationship came from
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_strength CHECK (strength >= 0.0 AND strength <= 1.0),
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT no_self_loop CHECK (source_entity_id != target_entity_id),
    UNIQUE (source_entity_id, target_entity_id, relationship_type)
);

COMMENT ON TABLE statedb.entity_relationships IS 'Graph edges connecting entities with typed relationships';
COMMENT ON COLUMN statedb.entity_relationships.strength IS 'Relationship strength (0.0 = weak, 1.0 = strong)';
COMMENT ON COLUMN statedb.entity_relationships.confidence IS 'Confidence in this relationship (0.0 = uncertain, 1.0 = certain)';
COMMENT ON COLUMN statedb.entity_relationships.evidence_count IS 'Number of times this relationship was observed';
COMMENT ON COLUMN statedb.entity_relationships.provenance IS 'Source of relationship: "dialogue:123", "training_log:456"';

-- ============================================================================
-- Table 3: entity_mentions
-- ============================================================================
-- Cross-reference table linking entities to logs/dialogues/memories
CREATE TABLE IF NOT EXISTS statedb.entity_mentions (
    mention_id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES statedb.entities(entity_id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,  -- 'training_log', 'dialogue', 'user_memory'
    source_id INTEGER NOT NULL,        -- ID in the source table
    session_id VARCHAR(255),
    turn_number INTEGER,
    mention_context TEXT,              -- Surrounding text where entity was mentioned
    extraction_method VARCHAR(50),     -- 'rule', 'llm', 'manual'
    confidence FLOAT DEFAULT 0.8,      -- Extraction confidence
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_source_type CHECK (source_type IN ('training_log', 'dialogue', 'user_memory')),
    CONSTRAINT valid_extraction_method CHECK (extraction_method IN ('rule', 'llm', 'manual')),
    CONSTRAINT valid_mention_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

COMMENT ON TABLE statedb.entity_mentions IS 'Links entities to logs, dialogues, and memories where they appear';
COMMENT ON COLUMN statedb.entity_mentions.source_type IS 'Type of record: training_log, dialogue, or user_memory';
COMMENT ON COLUMN statedb.entity_mentions.source_id IS 'ID in the corresponding source table';
COMMENT ON COLUMN statedb.entity_mentions.extraction_method IS 'How entity was extracted: rule-based, LLM, or manual';

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Entity indexes
CREATE INDEX IF NOT EXISTS idx_entities_type ON statedb.entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_canonical_name ON statedb.entities(canonical_name);
CREATE INDEX IF NOT EXISTS idx_entities_importance ON statedb.entities(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_entities_community ON statedb.entities(community_id) WHERE community_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entities_mention_count ON statedb.entities(mention_count DESC);

-- Vector similarity index using IVFFlat
-- Note: IVFFlat requires tuning 'lists' parameter based on data size
-- For < 1M rows: lists = rows / 1000 (we'll start with 100)
CREATE INDEX IF NOT EXISTS idx_entities_embedding ON statedb.entities
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

COMMENT ON INDEX statedb.idx_entities_embedding IS 'IVFFlat index for fast cosine similarity search';

-- Relationship indexes
CREATE INDEX IF NOT EXISTS idx_relationships_source ON statedb.entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON statedb.entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON statedb.entity_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_strength ON statedb.entity_relationships(strength DESC);

-- Mention indexes
CREATE INDEX IF NOT EXISTS idx_mentions_entity ON statedb.entity_mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_source ON statedb.entity_mentions(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_mentions_session ON statedb.entity_mentions(session_id) WHERE session_id IS NOT NULL;

-- ============================================================================
-- Add columns to existing tables for Graph RAG integration
-- ============================================================================

-- Add embedding and entity references to training_logs
DO $$
BEGIN
    -- Add embedding column if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'training_logs'
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE public.training_logs ADD COLUMN embedding vector(1536);
    END IF;

    -- Add mentioned_entity_ids array if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'training_logs'
        AND column_name = 'mentioned_entity_ids'
    ) THEN
        ALTER TABLE public.training_logs ADD COLUMN mentioned_entity_ids INTEGER[] DEFAULT '{}';
    END IF;
END $$;

-- Add embedding and entity references to dialogues
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'statedb'
        AND table_name = 'dialogues'
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE statedb.dialogues ADD COLUMN embedding vector(1536);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'statedb'
        AND table_name = 'dialogues'
        AND column_name = 'mentioned_entity_ids'
    ) THEN
        ALTER TABLE statedb.dialogues ADD COLUMN mentioned_entity_ids INTEGER[] DEFAULT '{}';
    END IF;
END $$;

-- Add embedding and entity references to user_memories
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'statedb'
        AND table_name = 'user_memories'
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE statedb.user_memories ADD COLUMN embedding vector(1536);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'statedb'
        AND table_name = 'user_memories'
        AND column_name = 'related_entity_ids'
    ) THEN
        ALTER TABLE statedb.user_memories ADD COLUMN related_entity_ids INTEGER[] DEFAULT '{}';
    END IF;
END $$;

-- Indexes for entity reference arrays (GIN for array operations)
CREATE INDEX IF NOT EXISTS idx_training_logs_entities ON public.training_logs
USING gin(mentioned_entity_ids);

CREATE INDEX IF NOT EXISTS idx_dialogues_entities ON statedb.dialogues
USING gin(mentioned_entity_ids);

CREATE INDEX IF NOT EXISTS idx_user_memories_entities ON statedb.user_memories
USING gin(related_entity_ids);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Show created tables
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'statedb'
AND tablename IN ('entities', 'entity_relationships', 'entity_mentions')
ORDER BY tablename;

-- Show new columns
SELECT
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema IN ('statedb', 'public')
AND table_name IN ('training_logs', 'dialogues', 'user_memories', 'entities')
AND column_name IN ('embedding', 'mentioned_entity_ids', 'related_entity_ids')
ORDER BY table_schema, table_name, column_name;

-- ============================================================================
-- Expected Output:
-- - 3 new tables: entities, entity_relationships, entity_mentions
-- - Columns added to: training_logs, dialogues, user_memories
-- - Indexes created for vector search and array operations
-- ============================================================================
