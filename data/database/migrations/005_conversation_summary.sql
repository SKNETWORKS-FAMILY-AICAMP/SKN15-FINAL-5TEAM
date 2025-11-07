-- Conversation Summary for Long-term Memory
-- 대화 요약을 위한 컬럼 추가

-- sessions 테이블에 conversation_summary 컬럼 추가
ALTER TABLE statedb.sessions
ADD COLUMN IF NOT EXISTS conversation_summary TEXT DEFAULT '';

-- summary_updated_at 컬럼 추가 (마지막 요약 시간)
ALTER TABLE statedb.sessions
ADD COLUMN IF NOT EXISTS summary_updated_at TIMESTAMP;

-- summary_turn_count 컬럼 추가 (요약에 포함된 턴 수)
ALTER TABLE statedb.sessions
ADD COLUMN IF NOT EXISTS summary_turn_count INT DEFAULT 0;

-- 주석 추가
COMMENT ON COLUMN statedb.sessions.conversation_summary IS '대화 요약 (장기기억용)';
COMMENT ON COLUMN statedb.sessions.summary_updated_at IS '마지막 요약 업데이트 시간';
COMMENT ON COLUMN statedb.sessions.summary_turn_count IS '요약에 포함된 대화 턴 수';
