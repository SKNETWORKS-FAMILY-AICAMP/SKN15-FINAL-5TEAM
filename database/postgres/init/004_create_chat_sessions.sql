-- 세션별 상태를 저장하여 대화 진행 상태를 추적

-- 기존 public.chat_sessions가 있을 경우 제거
DROP TABLE IF EXISTS public.chat_sessions CASCADE;

CREATE TABLE IF NOT EXISTS conversation.chat_sessions (
    id VARCHAR(255) PRIMARY KEY,  -- UUID session_id
    user_id VARCHAR(255) NOT NULL,
    scenario_id VARCHAR(255) NOT NULL,

    -- 세션 상태 (JSONB로 저장)
    state JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_interaction_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 인덱스용
    is_active BOOLEAN DEFAULT TRUE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON conversation.chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_scenario_id ON conversation.chat_sessions(scenario_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON conversation.chat_sessions(updated_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_is_active ON conversation.chat_sessions(is_active);

-- updated_at 자동 업데이트 트리거
DROP FUNCTION IF EXISTS conversation.update_chat_sessions_updated_at() CASCADE;

CREATE OR REPLACE FUNCTION conversation.update_chat_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.last_interaction_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chat_sessions_updated_at
    BEFORE UPDATE ON conversation.chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION conversation.update_chat_sessions_updated_at();
