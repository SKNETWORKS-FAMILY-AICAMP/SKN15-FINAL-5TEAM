-- Dialogues Table Migration
-- Created: 2025-11-12
-- Purpose: Add missing columns to conversation.dialogues table

-- Add missing columns to dialogues table
ALTER TABLE conversation.dialogues
ADD COLUMN IF NOT EXISTS user_id UUID,
ADD COLUMN IF NOT EXISTS scenario_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS stage_tag VARCHAR(100),
ADD COLUMN IF NOT EXISTS affinity_delta FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Rename timestamp to match other tables (optional - keep both for now)
-- Note: We're keeping 'timestamp' column for backward compatibility
-- and adding 'created_at' as the primary timestamp field

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_dialogues_session_user ON conversation.dialogues(session_id, user_id);
CREATE INDEX IF NOT EXISTS idx_dialogues_user_created ON conversation.dialogues(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_dialogues_session_turn ON conversation.dialogues(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_dialogues_scenario ON conversation.dialogues(scenario_id);

-- Add comments
COMMENT ON COLUMN conversation.dialogues.user_id IS '사용자 ID';
COMMENT ON COLUMN conversation.dialogues.scenario_id IS '시나리오 ID';
COMMENT ON COLUMN conversation.dialogues.stage_tag IS '스테이지 태그';
COMMENT ON COLUMN conversation.dialogues.affinity_delta IS '친밀도 변화량';
COMMENT ON COLUMN conversation.dialogues.created_at IS '생성 시각';
COMMENT ON COLUMN conversation.dialogues.updated_at IS '수정 시각';
