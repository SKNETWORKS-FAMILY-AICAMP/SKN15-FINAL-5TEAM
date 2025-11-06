-- ============================================================================
-- Migration: 020_game_content_data
-- Description: Create tables for game content data (characters, scenario beats, images)
-- Purpose: Move data from JSON files to database
-- Date: 2025-11-06
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Characters Table (캐릭터 마스터 데이터)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.characters (
    character_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    personality TEXT,
    breathing_style VARCHAR(100),
    default_affinity INT DEFAULT 500,

    -- Appearance
    appearance_hair TEXT,
    appearance_eyes TEXT,
    appearance_distinctive TEXT,
    appearance_impression TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE content.characters IS 'Character master data with personality and appearance';
COMMENT ON COLUMN content.characters.default_affinity IS 'Default affinity level (0-1000)';

-- ============================================================================
-- 2. Character Core Values (핵심 가치관)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.character_core_values (
    id SERIAL PRIMARY KEY,
    character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    value_text TEXT NOT NULL,
    display_order INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_character_core_values_char ON content.character_core_values(character_id);

-- ============================================================================
-- 3. Character Emotional Triggers (감정 트리거)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.character_emotional_triggers (
    id SERIAL PRIMARY KEY,
    character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    emotion_type VARCHAR(50) NOT NULL,  -- 'anger', 'compassion', 'determination'
    trigger_text TEXT NOT NULL,
    display_order INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_character_triggers_char ON content.character_emotional_triggers(character_id);

-- ============================================================================
-- 4. Character Tone Settings (호감도별 말투)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.character_tone (
    id SERIAL PRIMARY KEY,
    character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    affinity_level VARCHAR(20) NOT NULL,  -- 'low', 'mid', 'high'
    level_range_min INT NOT NULL,
    level_range_max INT NOT NULL,
    style TEXT NOT NULL,
    calling VARCHAR(50),
    suffix VARCHAR(50),
    samples JSONB,  -- Array of sample dialogues

    CONSTRAINT unique_char_tone UNIQUE(character_id, affinity_level)
);

CREATE INDEX IF NOT EXISTS idx_character_tone_char ON content.character_tone(character_id);

-- ============================================================================
-- 5. Character Aliases (별칭)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.character_aliases (
    id SERIAL PRIMARY KEY,
    character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,

    CONSTRAINT unique_alias UNIQUE(alias)
);

CREATE INDEX IF NOT EXISTS idx_character_aliases_char ON content.character_aliases(character_id);

-- ============================================================================
-- 6. Character Quotes (명대사)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.character_quotes (
    id SERIAL PRIMARY KEY,
    character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    quote_text TEXT NOT NULL,
    display_order INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_character_quotes_char ON content.character_quotes(character_id);

-- ============================================================================
-- 7. Character Intent Rules (의도 규칙 - AI용)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.character_intent_rules (
    id SERIAL PRIMARY KEY,
    character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    rule_category VARCHAR(50) NOT NULL,  -- 'weights', 'sensitivities', 'patterns'
    rule_type VARCHAR(100) NOT NULL,     -- 'positive_core', 'contempt_blame', etc.
    rule_value JSONB NOT NULL,           -- Weights (float), patterns (array), etc.

    CONSTRAINT unique_char_rule UNIQUE(character_id, rule_category, rule_type)
);

CREATE INDEX IF NOT EXISTS idx_character_intent_char ON content.character_intent_rules(character_id);

-- ============================================================================
-- 8. Character Relationships (캐릭터 간 관계 - 시나리오별)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.character_relationships (
    id SERIAL PRIMARY KEY,
    scenario_id VARCHAR(50) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE,
    character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    target_character_id VARCHAR(50) REFERENCES content.characters(character_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,  -- 'ally', 'enemy', 'respect', 'love'
    description TEXT,

    CONSTRAINT unique_scenario_char_rel UNIQUE(scenario_id, character_id, target_character_id)
);

CREATE INDEX IF NOT EXISTS idx_char_rel_scenario ON content.character_relationships(scenario_id);
CREATE INDEX IF NOT EXISTS idx_char_rel_char ON content.character_relationships(character_id);

-- ============================================================================
-- 9. Scenario Beats (시나리오 비트 - 대화 흐름)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.scenario_beats (
    beat_id VARCHAR(100) PRIMARY KEY,
    scenario_id VARCHAR(50) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE,
    beat_name VARCHAR(255) NOT NULL,
    beat_category VARCHAR(50),  -- 'dialogue', 'battle', 'cutscene'
    display_order INT DEFAULT 0,
    parent_beat_id VARCHAR(100),  -- For nested beats

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenario_beats_scenario ON content.scenario_beats(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_beats_parent ON content.scenario_beats(parent_beat_id);

-- ============================================================================
-- 10. Beat Goals (비트별 목표/대사)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.beat_goals (
    id SERIAL PRIMARY KEY,
    beat_id VARCHAR(100) REFERENCES content.scenario_beats(beat_id) ON DELETE CASCADE,
    goal_text TEXT NOT NULL,
    speaker_hints JSONB,  -- Array of character_ids
    fx VARCHAR(100),      -- Visual/audio effect
    display_order INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_beat_goals_beat ON content.beat_goals(beat_id);

-- ============================================================================
-- 11. Image Mappings (이미지 매핑)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.image_mappings (
    id SERIAL PRIMARY KEY,
    scenario_id VARCHAR(50) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE,
    mapping_category VARCHAR(50) NOT NULL,  -- 'character', 'bg', 'cutscene'
    image_key VARCHAR(255) NOT NULL,        -- 'rengoku_normal', 'train_bg_1'
    image_url TEXT NOT NULL,                -- S3 URL or local path
    metadata JSONB,                         -- Additional data (resolution, mood, etc.)

    CONSTRAINT unique_scenario_image UNIQUE(scenario_id, mapping_category, image_key)
);

CREATE INDEX IF NOT EXISTS idx_image_mappings_scenario ON content.image_mappings(scenario_id);
CREATE INDEX IF NOT EXISTS idx_image_mappings_category ON content.image_mappings(mapping_category);

-- ============================================================================
-- 12. World Data (세계관 설정)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.worlds (
    world_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    era VARCHAR(100),             -- 'Taisho Era', 'Modern', etc.
    lore JSONB,                   -- World lore data

    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE content.worlds IS 'World/universe settings for scenarios';

-- Link scenarios to worlds
ALTER TABLE content.scenarios
  ADD COLUMN IF NOT EXISTS world_id VARCHAR(50) REFERENCES content.worlds(world_id);

CREATE INDEX IF NOT EXISTS idx_scenarios_world ON content.scenarios(world_id);

-- Add additional scenario metadata columns (from JSON migration)
ALTER TABLE content.scenarios
  ADD COLUMN IF NOT EXISTS emoji VARCHAR(10),
  ADD COLUMN IF NOT EXISTS detail_description TEXT,
  ADD COLUMN IF NOT EXISTS category VARCHAR(100),
  ADD COLUMN IF NOT EXISTS mood TEXT[],
  ADD COLUMN IF NOT EXISTS implemented BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS likes INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS comments INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS views INT DEFAULT 0;

-- ============================================================================
-- 14. Scenario Characters Junction Table (시나리오-캐릭터 관계)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.scenario_characters (
    id SERIAL PRIMARY KEY,
    scenario_id VARCHAR(50) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE,
    character_name VARCHAR(100) NOT NULL,
    character_image VARCHAR(500),
    greeting TEXT,
    status VARCHAR(100),
    color VARCHAR(50),
    display_order INT DEFAULT 0,

    CONSTRAINT unique_scenario_char UNIQUE(scenario_id, character_name)
);

CREATE INDEX IF NOT EXISTS idx_scenario_characters_scenario ON content.scenario_characters(scenario_id);

-- ============================================================================
-- 13. Trigger Functions
-- ============================================================================

-- Update updated_at on characters
CREATE OR REPLACE FUNCTION update_character_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_character_timestamp
BEFORE UPDATE ON content.characters
FOR EACH ROW
EXECUTE FUNCTION update_character_updated_at();

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

\echo '============================================================'
\echo '✅ Game Content Data Tables Created'
\echo '============================================================'
\echo ''
\echo 'Tables created in content schema:'

SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('content.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'content'
  AND tablename LIKE 'character%' OR tablename LIKE 'beat%' OR tablename LIKE 'image%' OR tablename = 'worlds'
ORDER BY tablename;

\echo ''
\echo 'Next steps:'
\echo '  1. Run seed script to migrate JSON data'
\echo '  2. Update code to use database instead of JSON files'
\echo '  3. Test character loading'
\echo '  4. Test scenario loading'
