-- ============================================================================
-- Migration: 006_user_memories
-- Description: Create user-level long-term memory system
-- Created: 2025-10-31
-- Purpose: Store personalized memories across sessions for each user
-- ============================================================================

-- Problem 4: Long-term Memory System
-- This migration creates a table for storing user-specific memories that persist
-- across multiple sessions, enabling personalized AI interactions

-- ============================================================================
-- 1. User Memories Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS statedb.user_memories (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- User reference
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,

    -- Memory categorization
    memory_key VARCHAR(100) NOT NULL,  -- Category: 'character_relationship', 'user_preference', 'story_progress', etc.
    memory_type VARCHAR(50) DEFAULT 'fact',  -- 'fact', 'preference', 'relationship', 'event', 'goal'

    -- Memory content
    memory_value TEXT NOT NULL,  -- The actual memory content
    context JSONB,  -- Additional structured context

    -- Importance and relevance
    importance FLOAT CHECK (importance >= 0.0 AND importance <= 1.0) DEFAULT 0.5,  -- How important this memory is (0.0 ~ 1.0)
    access_count INT DEFAULT 0,  -- How many times this memory was accessed
    last_accessed_at TIMESTAMP,  -- When this memory was last retrieved

    -- Source tracking
    source_session_id UUID,  -- Session where this memory originated
    related_session_ids UUID[],  -- All sessions that contributed to or accessed this memory

    -- Temporal data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Memory lifecycle
    is_active BOOLEAN DEFAULT TRUE,  -- Whether this memory is still relevant
    expires_at TIMESTAMP,  -- Optional expiration date for temporary memories

    -- Metadata
    tags VARCHAR(50)[],  -- Searchable tags for categorization
    confidence FLOAT CHECK (confidence >= 0.0 AND confidence <= 1.0),  -- Confidence in this memory (if auto-extracted)

    -- Constraints
    CONSTRAINT unique_user_memory_key UNIQUE(user_id, memory_key)
);

-- ============================================================================
-- 2. Indexes for Performance
-- ============================================================================

-- Most common queries: filter by user_id, memory_type, and importance
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id
    ON statedb.user_memories(user_id);

CREATE INDEX IF NOT EXISTS idx_user_memories_memory_type
    ON statedb.user_memories(memory_type);

CREATE INDEX IF NOT EXISTS idx_user_memories_importance
    ON statedb.user_memories(importance DESC)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_user_memories_user_importance
    ON statedb.user_memories(user_id, importance DESC)
    WHERE is_active = TRUE;

-- Index for tag-based queries
CREATE INDEX IF NOT EXISTS idx_user_memories_tags_gin
    ON statedb.user_memories USING GIN (tags);

-- Index for JSONB context queries
CREATE INDEX IF NOT EXISTS idx_user_memories_context_gin
    ON statedb.user_memories USING GIN (context);

-- Index for active memories sorted by last access
CREATE INDEX IF NOT EXISTS idx_user_memories_active_recent
    ON statedb.user_memories(user_id, last_accessed_at DESC)
    WHERE is_active = TRUE;

-- Index for session tracking
CREATE INDEX IF NOT EXISTS idx_user_memories_source_session
    ON statedb.user_memories(source_session_id);

-- ============================================================================
-- 3. Trigger for Automatic updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION statedb.update_user_memories_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_memories_updated_at
    BEFORE UPDATE ON statedb.user_memories
    FOR EACH ROW
    EXECUTE FUNCTION statedb.update_user_memories_timestamp();

-- ============================================================================
-- 4. Comments for Documentation
-- ============================================================================

COMMENT ON TABLE statedb.user_memories IS 'User-level long-term memories that persist across sessions for personalized AI interactions';
COMMENT ON COLUMN statedb.user_memories.user_id IS 'User who owns this memory';
COMMENT ON COLUMN statedb.user_memories.memory_key IS 'Category/key for this memory (e.g., character_relationship:tanjiro, user_preference:tone)';
COMMENT ON COLUMN statedb.user_memories.memory_type IS 'Type of memory: fact, preference, relationship, event, goal';
COMMENT ON COLUMN statedb.user_memories.memory_value IS 'The actual memory content in natural language';
COMMENT ON COLUMN statedb.user_memories.context IS 'Additional structured metadata (JSONB)';
COMMENT ON COLUMN statedb.user_memories.importance IS 'Importance score 0.0-1.0 (higher = more important for retrieval)';
COMMENT ON COLUMN statedb.user_memories.access_count IS 'Number of times this memory was retrieved';
COMMENT ON COLUMN statedb.user_memories.is_active IS 'Whether this memory is still relevant (can be archived without deletion)';
COMMENT ON COLUMN statedb.user_memories.confidence IS 'Confidence score for auto-extracted memories (0.0-1.0)';

-- ============================================================================
-- 5. Sample Queries (for reference)
-- ============================================================================

-- Query 1: Get all active memories for a user, sorted by importance
/*
SELECT
    memory_key,
    memory_value,
    importance,
    last_accessed_at,
    tags
FROM statedb.user_memories
WHERE user_id = 'eeae5eb1-...'
  AND is_active = TRUE
ORDER BY importance DESC, last_accessed_at DESC NULLS LAST
LIMIT 20;
*/

-- Query 2: Get character relationship memories
/*
SELECT
    memory_key,
    memory_value,
    context->>'character_name' as character,
    context->>'affinity_score' as affinity,
    importance
FROM statedb.user_memories
WHERE user_id = 'eeae5eb1-...'
  AND memory_type = 'relationship'
  AND is_active = TRUE
ORDER BY importance DESC;
*/

-- Query 3: Search memories by tag
/*
SELECT
    memory_key,
    memory_value,
    tags,
    importance
FROM statedb.user_memories
WHERE user_id = 'eeae5eb1-...'
  AND tags @> ARRAY['tanjiro']
  AND is_active = TRUE
ORDER BY importance DESC;
*/

-- Query 4: Update memory importance based on access patterns
/*
UPDATE statedb.user_memories
SET
    importance = LEAST(1.0, importance + 0.05),  -- Increase importance by 5% (max 1.0)
    access_count = access_count + 1,
    last_accessed_at = CURRENT_TIMESTAMP
WHERE id = 123;
*/

-- Query 5: Archive old, low-importance memories
/*
UPDATE statedb.user_memories
SET is_active = FALSE
WHERE user_id = 'eeae5eb1-...'
  AND importance < 0.3
  AND last_accessed_at < NOW() - INTERVAL '90 days';
*/

-- Query 6: Get memory context for a new session
/*
SELECT
    jsonb_build_object(
        'relationships', (
            SELECT jsonb_agg(jsonb_build_object(
                'character', context->>'character_name',
                'note', memory_value
            ))
            FROM statedb.user_memories
            WHERE user_id = 'eeae5eb1-...'
              AND memory_type = 'relationship'
              AND is_active = TRUE
            ORDER BY importance DESC
            LIMIT 5
        ),
        'preferences', (
            SELECT jsonb_agg(jsonb_build_object(
                'key', memory_key,
                'value', memory_value
            ))
            FROM statedb.user_memories
            WHERE user_id = 'eeae5eb1-...'
              AND memory_type = 'preference'
              AND is_active = TRUE
            ORDER BY importance DESC
            LIMIT 5
        ),
        'story_progress', (
            SELECT jsonb_agg(jsonb_build_object(
                'event', memory_value,
                'context', context
            ))
            FROM statedb.user_memories
            WHERE user_id = 'eeae5eb1-...'
              AND memory_type = 'event'
              AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 10
        )
    ) as user_memory_context;
*/

-- ============================================================================
-- 6. Example Data (for testing)
-- ============================================================================

/*
-- Example 1: Character relationship memory
INSERT INTO statedb.user_memories (
    user_id,
    memory_key,
    memory_type,
    memory_value,
    context,
    importance,
    source_session_id,
    tags
) VALUES (
    'eeae5eb1-...',
    'character_relationship:tanjiro',
    'relationship',
    '탄지로와 매우 친밀한 관계. 사용자는 탄지로의 조언을 잘 따르고 신뢰한다.',
    '{"character_name": "tanjiro", "affinity_score": 85, "interactions": 15}'::jsonb,
    0.9,
    '7d531ee1-...',
    ARRAY['tanjiro', 'high_affinity', 'main_character']
);

-- Example 2: User preference memory
INSERT INTO statedb.user_memories (
    user_id,
    memory_key,
    memory_type,
    memory_value,
    importance,
    tags
) VALUES (
    'eeae5eb1-...',
    'user_preference:conversation_style',
    'preference',
    '친근하고 장난스러운 대화 스타일을 선호함. 격식 있는 말투보다 편한 말투를 좋아함.',
    0.8,
    ARRAY['conversation', 'tone', 'friendly']
);

-- Example 3: Story progress memory
INSERT INTO statedb.user_memories (
    user_id,
    memory_key,
    memory_type,
    memory_value,
    context,
    importance,
    tags
) VALUES (
    'eeae5eb1-...',
    'story_progress:train_prelude_completed',
    'event',
    'TRAIN_PRELUDE 스테이지 완료. 탄지로와 함께 기차에 탑승하여 임무를 시작함.',
    '{"stage": "TRAIN_PRELUDE", "completion_date": "2025-10-31", "ending": null}'::jsonb,
    0.7,
    ARRAY['train', 'story', 'completed']
);
*/

-- ============================================================================
-- 7. Data Retention and Cleanup
-- ============================================================================

-- Function to archive old, unused memories
CREATE OR REPLACE FUNCTION statedb.archive_old_memories(
    days_inactive INT DEFAULT 90,
    min_importance FLOAT DEFAULT 0.3
)
RETURNS INT AS $$
DECLARE
    archived_count INT;
BEGIN
    UPDATE statedb.user_memories
    SET is_active = FALSE
    WHERE is_active = TRUE
      AND importance < min_importance
      AND (
          last_accessed_at < NOW() - (days_inactive || ' days')::INTERVAL
          OR (last_accessed_at IS NULL AND created_at < NOW() - (days_inactive || ' days')::INTERVAL)
      );

    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION statedb.archive_old_memories IS 'Archives old, low-importance memories that haven''t been accessed recently';

-- Function to permanently delete expired memories
CREATE OR REPLACE FUNCTION statedb.delete_expired_memories()
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM statedb.user_memories
    WHERE expires_at IS NOT NULL
      AND expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION statedb.delete_expired_memories IS 'Permanently deletes memories that have passed their expiration date';

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Verify table creation
SELECT
    table_schema,
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) as size
FROM information_schema.tables
WHERE table_schema = 'statedb'
  AND table_name = 'user_memories';

-- Verify indexes
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'statedb'
  AND tablename = 'user_memories'
ORDER BY indexname;

-- Verify triggers
SELECT
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'statedb'
  AND event_object_table = 'user_memories';

COMMENT ON SCHEMA statedb IS 'StateDB schema with user-level long-term memory system - Phase 4+';
