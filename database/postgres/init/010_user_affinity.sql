-- ============================================================================
-- User Character Affinity Table
-- Created: 2025-11-12
-- Purpose: Track user global affinity with characters
-- ============================================================================

CREATE TABLE IF NOT EXISTS progression.user_character_affinity (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    character_name VARCHAR(255) NOT NULL,
    total_affinity_score INTEGER NOT NULL DEFAULT 0,
    affinity_level INTEGER NOT NULL DEFAULT 1,
    total_interactions INTEGER NOT NULL DEFAULT 0,
    last_interaction_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT user_character_affinity_unique UNIQUE (user_id, character_name),
    CONSTRAINT user_character_affinity_score_check CHECK (total_affinity_score >= 0 AND total_affinity_score <= 1000),
    CONSTRAINT user_character_affinity_level_check CHECK (affinity_level >= 1 AND affinity_level <= 10)
);

CREATE INDEX IF NOT EXISTS idx_user_character_affinity_user ON progression.user_character_affinity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_character_affinity_character ON progression.user_character_affinity(character_name);
CREATE INDEX IF NOT EXISTS idx_user_character_affinity_score ON progression.user_character_affinity(user_id, total_affinity_score);

COMMENT ON TABLE progression.user_character_affinity IS '사용자별 캐릭터 글로벌 친밀도';
COMMENT ON COLUMN progression.user_character_affinity.total_affinity_score IS '총 친밀도 점수 (0-1000)';
COMMENT ON COLUMN progression.user_character_affinity.affinity_level IS '친밀도 레벨 (1-10)';

\echo '✅ User character affinity table created'
