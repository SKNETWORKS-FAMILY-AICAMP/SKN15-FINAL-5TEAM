-- ============================================================================
-- Migration: 002_logdb_training_logs
-- Description: Create LogDB schema for AI training data collection
-- Created: 2025-10-30
-- Purpose: SLLM LoRA fine-tuning data collection with automatic labeling
-- ============================================================================

-- Phase 4: AI Training Log System
-- This migration creates tables for collecting training data from agents
-- to be used for LoRA fine-tuning of small language models

-- ============================================================================
-- 1. LogDB Database Creation (if not exists)
-- ============================================================================

-- Note: RDS에서 이미 kime_logdb를 생성했다면 이 부분은 건너뜁니다
-- CREATE DATABASE kime_logdb;

-- LogDB 연결 후 진행
-- \c kime_logdb;

-- ============================================================================
-- 2. Training Logs Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS training_logs (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Session context
    session_id UUID NOT NULL,
    turn_count INT NOT NULL,
    scenario_id VARCHAR(50),
    current_stage VARCHAR(100),

    -- Agent information
    agent_name VARCHAR(50) NOT NULL,  -- 'router', 'parent', 'children', 'dialogue'

    -- Input data (for learning)
    user_input TEXT,
    context JSONB NOT NULL,  -- State snapshot at the time of execution

    -- Model output
    model_output JSONB NOT NULL,  -- Agent response/decision

    -- Performance metrics
    latency_ms INT,  -- Execution time in milliseconds
    token_count INT,  -- Total tokens used (input + output)
    llm_model VARCHAR(100),  -- Model used (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet')

    -- Auto-labeling (for supervised learning)
    outcome VARCHAR(20),  -- 'success', 'failure', 'partial', null (unlabeled)
    outcome_reason TEXT,  -- Why this outcome was labeled
    feedback_score FLOAT CHECK (feedback_score >= 0.0 AND feedback_score <= 1.0),  -- 0.0 ~ 1.0

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    labeled_at TIMESTAMP,  -- When auto-labeling was applied

    -- Additional flags
    is_error BOOLEAN DEFAULT FALSE,
    error_message TEXT
);

-- ============================================================================
-- 3. Indexes for Performance
-- ============================================================================

-- Most common queries: filter by agent, outcome, time range
CREATE INDEX IF NOT EXISTS idx_training_logs_agent_name
    ON training_logs(agent_name);

CREATE INDEX IF NOT EXISTS idx_training_logs_outcome
    ON training_logs(outcome)
    WHERE outcome IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_training_logs_created_at
    ON training_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_training_logs_session_id
    ON training_logs(session_id);

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_training_logs_agent_outcome_time
    ON training_logs(agent_name, outcome, created_at DESC);

-- GIN index for JSONB queries (context and model_output)
CREATE INDEX IF NOT EXISTS idx_training_logs_context_gin
    ON training_logs USING GIN (context);

CREATE INDEX IF NOT EXISTS idx_training_logs_model_output_gin
    ON training_logs USING GIN (model_output);

-- ============================================================================
-- 4. Comments for Documentation
-- ============================================================================

COMMENT ON TABLE training_logs IS 'Training data for SLLM LoRA fine-tuning with automatic outcome labeling';
COMMENT ON COLUMN training_logs.session_id IS 'Session UUID to group conversation turns';
COMMENT ON COLUMN training_logs.turn_count IS 'Turn number in the conversation';
COMMENT ON COLUMN training_logs.agent_name IS 'Agent that generated this log (router, parent, children, dialogue)';
COMMENT ON COLUMN training_logs.context IS 'State snapshot (JSONB) - input for the model';
COMMENT ON COLUMN training_logs.model_output IS 'Agent response/decision (JSONB) - expected output for training';
COMMENT ON COLUMN training_logs.outcome IS 'Auto-labeled outcome: success (좋은 예시), failure (나쁜 예시), partial (애매한 예시)';
COMMENT ON COLUMN training_logs.feedback_score IS 'Quality score 0.0-1.0 for weighted learning';

-- ============================================================================
-- 5. User Feedback Table (Optional - for human-in-the-loop labeling)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGSERIAL PRIMARY KEY,
    training_log_id BIGINT REFERENCES training_logs(id) ON DELETE CASCADE,

    -- Feedback type
    feedback_type VARCHAR(50) NOT NULL,  -- 'thumbs_up', 'thumbs_down', 'report_issue'
    feedback_text TEXT,

    -- User info (optional, can be anonymous)
    user_id VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_log_id
    ON user_feedback(training_log_id);

CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at
    ON user_feedback(created_at DESC);

COMMENT ON TABLE user_feedback IS 'Human feedback for improving auto-labeling and training data quality';

-- ============================================================================
-- 6. Sample Queries (for reference)
-- ============================================================================

-- Query 1: Extract Router training data
/*
SELECT
    user_input,
    context->>'scenario_id' as scenario_id,
    context->>'current_stage' as current_stage,
    model_output->>'classification' as classification,
    model_output->>'next_node' as next_node,
    outcome,
    feedback_score
FROM training_logs
WHERE agent_name = 'router'
  AND outcome = 'success'
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 1000;
*/

-- Query 2: Find high-quality Parent Agent examples
/*
SELECT
    session_id,
    turn_count,
    context->>'current_stage' as stage,
    model_output->>'agent_inputs' as agent_inputs,
    feedback_score,
    latency_ms
FROM training_logs
WHERE agent_name = 'parent'
  AND outcome = 'success'
  AND feedback_score > 0.8
ORDER BY feedback_score DESC, latency_ms ASC
LIMIT 500;
*/

-- Query 3: Identify failure patterns
/*
SELECT
    agent_name,
    outcome_reason,
    COUNT(*) as count,
    AVG(latency_ms) as avg_latency,
    AVG(token_count) as avg_tokens
FROM training_logs
WHERE outcome = 'failure'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY agent_name, outcome_reason
ORDER BY count DESC;
*/

-- Query 4: Training dataset export (Router Agent)
/*
-- For LoRA fine-tuning format
SELECT
    jsonb_build_object(
        'prompt', user_input,
        'context', context,
        'completion', model_output,
        'weight', feedback_score
    ) as training_example
FROM training_logs
WHERE agent_name = 'router'
  AND outcome IN ('success', 'partial')
  AND feedback_score >= 0.6
  AND created_at >= NOW() - INTERVAL '90 days'
ORDER BY RANDOM()  -- Shuffle for training
LIMIT 10000;
*/

-- ============================================================================
-- 7. Data Retention Policy (Optional - for compliance)
-- ============================================================================

-- Delete training logs older than 1 year (can be run as a cron job)
/*
DELETE FROM training_logs
WHERE created_at < NOW() - INTERVAL '365 days';
*/

-- Archive old logs to S3 before deletion (recommended)
/*
-- Use pg_dump or COPY command
COPY (
    SELECT * FROM training_logs
    WHERE created_at < NOW() - INTERVAL '365 days'
) TO '/tmp/training_logs_archive_2024.csv' CSV HEADER;
-- Then upload to S3 and delete from DB
*/

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Verify table creation
SELECT
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('training_logs', 'user_feedback');

-- Verify indexes
SELECT
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE tablename IN ('training_logs', 'user_feedback')
ORDER BY tablename, indexname;

COMMENT ON SCHEMA public IS 'LogDB schema for AI training data - Phase 4';
