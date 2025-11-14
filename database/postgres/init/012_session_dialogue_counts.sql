--
-- Migration: Add dialogue count tracking columns to sessions table
-- Created: 2025-11-14
-- Purpose: Track total_dialogue_count and summary_dialogue_count for memory extraction
--

-- Add total_dialogue_count column
ALTER TABLE conversation.sessions
ADD COLUMN IF NOT EXISTS total_dialogue_count INTEGER DEFAULT 0;

-- Add summary_dialogue_count column
ALTER TABLE conversation.sessions
ADD COLUMN IF NOT EXISTS summary_dialogue_count INTEGER DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN conversation.sessions.total_dialogue_count IS '총 대화 개수 (AI + 사용자)';
COMMENT ON COLUMN conversation.sessions.summary_dialogue_count IS '마지막 요약 이후 대화 개수';

-- Create index for filtering sessions by dialogue count (optional, for analytics)
CREATE INDEX IF NOT EXISTS idx_sessions_dialogue_count
ON conversation.sessions(total_dialogue_count)
WHERE total_dialogue_count > 0;

-- Verify the migration
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_schema = 'conversation'
  AND table_name = 'sessions'
  AND column_name IN ('total_dialogue_count', 'summary_dialogue_count');
