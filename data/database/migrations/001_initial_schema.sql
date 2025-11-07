-- ============================================================
-- KIME Chat Database Schema
-- Version: 1.0
-- Description: Initial schema for StateDB and LogDB
-- ============================================================

-- ============================================================
-- StateDB Schema: 게임 상태 및 세션 데이터
-- ============================================================
CREATE SCHEMA IF NOT EXISTS statedb;

-- ------------------------------------------------------------
-- 1. sessions: 세션 메타데이터
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.sessions (
    session_id UUID PRIMARY KEY,
    scenario_id VARCHAR(255) NOT NULL,
    user_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    current_stage VARCHAR(255),
    turn_count INTEGER DEFAULT 0,
    stage_turn INTEGER DEFAULT 0,
    final_ending VARCHAR(255),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_sessions_scenario ON statedb.sessions(scenario_id);
CREATE INDEX idx_sessions_created ON statedb.sessions(created_at DESC);
CREATE INDEX idx_sessions_active ON statedb.sessions(is_active) WHERE is_active = true;

COMMENT ON TABLE statedb.sessions IS '사용자 세션 메타데이터';
COMMENT ON COLUMN statedb.sessions.session_id IS '세션 고유 ID';
COMMENT ON COLUMN statedb.sessions.scenario_id IS '현재 플레이 중인 시나리오 ID';
COMMENT ON COLUMN statedb.sessions.current_stage IS '현재 스테이지 ID';
COMMENT ON COLUMN statedb.sessions.turn_count IS '전체 대화 턴 수';
COMMENT ON COLUMN statedb.sessions.stage_turn IS '현재 스테이지 내 턴 수';

-- ------------------------------------------------------------
-- 2. user_inputs: 사용자 입력 히스토리
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.user_inputs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_inputs_session ON statedb.user_inputs(session_id, turn_number DESC);
CREATE INDEX idx_user_inputs_timestamp ON statedb.user_inputs(timestamp DESC);

COMMENT ON TABLE statedb.user_inputs IS '사용자 입력 히스토리';
COMMENT ON COLUMN statedb.user_inputs.turn_number IS '해당 세션 내 턴 번호';

-- ------------------------------------------------------------
-- 3. dialogues: 대화 기록
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.dialogues (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    speaker VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    emotion VARCHAR(100),
    emotion_intensity VARCHAR(50),
    order_index INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dialogues_session ON statedb.dialogues(session_id, turn_number, order_index);
CREATE INDEX idx_dialogues_speaker ON statedb.dialogues(speaker);
CREATE INDEX idx_dialogues_timestamp ON statedb.dialogues(timestamp DESC);

COMMENT ON TABLE statedb.dialogues IS '캐릭터 대화 기록';
COMMENT ON COLUMN statedb.dialogues.speaker IS '화자 ID (tanjiro, rengoku 등)';
COMMENT ON COLUMN statedb.dialogues.order_index IS '같은 턴 내 대화 순서';

-- ------------------------------------------------------------
-- 4. affinity_records: 친밀도 기록
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.affinity_records (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    character_name VARCHAR(255) NOT NULL,
    affinity_score INTEGER NOT NULL,
    change_amount INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_affinity_session ON statedb.affinity_records(session_id, character_name);
CREATE INDEX idx_affinity_character ON statedb.affinity_records(character_name);
CREATE INDEX idx_affinity_timestamp ON statedb.affinity_records(timestamp DESC);

COMMENT ON TABLE statedb.affinity_records IS '캐릭터 친밀도 변화 기록';
COMMENT ON COLUMN statedb.affinity_records.affinity_score IS '현재 친밀도 점수';
COMMENT ON COLUMN statedb.affinity_records.change_amount IS '이전 턴 대비 변화량';

-- ------------------------------------------------------------
-- 5. stage_progression: 스테이지 진행 상황
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.stage_progression (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    stage_id VARCHAR(255) NOT NULL,
    stage_order INTEGER NOT NULL,
    entered_at TIMESTAMP DEFAULT NOW(),
    exited_at TIMESTAMP NULL,
    dialogue_count INTEGER DEFAULT 0,
    stage_turn_count INTEGER DEFAULT 0
);

CREATE INDEX idx_stage_session ON statedb.stage_progression(session_id, stage_order DESC);
CREATE INDEX idx_stage_id ON statedb.stage_progression(stage_id);
CREATE INDEX idx_stage_active ON statedb.stage_progression(session_id) WHERE exited_at IS NULL;

COMMENT ON TABLE statedb.stage_progression IS '스테이지 진행 기록';
COMMENT ON COLUMN statedb.stage_progression.stage_order IS '스테이지 진입 순서';
COMMENT ON COLUMN statedb.stage_progression.dialogue_count IS '해당 스테이지에서 생성된 대화 수';

-- ------------------------------------------------------------
-- 6. game_events: 게임 이벤트 및 플래그
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.game_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_session ON statedb.game_events(session_id, turn_number DESC);
CREATE INDEX idx_events_type ON statedb.game_events(event_type);
CREATE INDEX idx_events_data ON statedb.game_events USING GIN (event_data);

COMMENT ON TABLE statedb.game_events IS '게임 이벤트 및 시스템 플래그';
COMMENT ON COLUMN statedb.game_events.event_type IS '이벤트 타입 (flag_set, mission_complete 등)';
COMMENT ON COLUMN statedb.game_events.event_data IS 'JSON 형식의 이벤트 상세 데이터';

-- ------------------------------------------------------------
-- 7. mission_records: 미션 기록
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.mission_records (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    mission_type VARCHAR(100) NOT NULL,
    target_character VARCHAR(255),
    attempt_count INTEGER DEFAULT 0,
    success BOOLEAN,
    completed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mission_session ON statedb.mission_records(session_id);
CREATE INDEX idx_mission_type ON statedb.mission_records(mission_type);
CREATE INDEX idx_mission_character ON statedb.mission_records(target_character);

COMMENT ON TABLE statedb.mission_records IS '미션 수행 기록 (RECRUIT 등)';
COMMENT ON COLUMN statedb.mission_records.mission_type IS '미션 타입 (RECRUIT, DEFEND 등)';
COMMENT ON COLUMN statedb.mission_records.target_character IS '미션 대상 캐릭터';

-- ------------------------------------------------------------
-- 8. session_snapshots: 세션 스냅샷 (복구용)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.session_snapshots (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    state_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (session_id, turn_number)
);

CREATE INDEX idx_snapshots_session ON statedb.session_snapshots(session_id, turn_number DESC);
CREATE INDEX idx_snapshots_created ON statedb.session_snapshots(created_at DESC);

COMMENT ON TABLE statedb.session_snapshots IS '세션 상태 스냅샷 (복구 및 분석용)';
COMMENT ON COLUMN statedb.session_snapshots.state_json IS '전체 GraphState를 JSON으로 저장';

-- ============================================================
-- LogDB Schema: 로그 및 모니터링
-- ============================================================
CREATE SCHEMA IF NOT EXISTS logdb;

-- ------------------------------------------------------------
-- 1. logs: 구조화된 애플리케이션 로그
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logdb.logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID,
    log_level VARCHAR(20) NOT NULL,
    stage_name VARCHAR(100),
    agent_name VARCHAR(100),
    message TEXT NOT NULL,
    context_data JSONB,
    duration_ms REAL,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_logs_timestamp ON logdb.logs(timestamp DESC);
CREATE INDEX idx_logs_level ON logdb.logs(log_level);
CREATE INDEX idx_logs_session ON logdb.logs(session_id);
CREATE INDEX idx_logs_stage ON logdb.logs(stage_name);
CREATE INDEX idx_logs_agent ON logdb.logs(agent_name);
CREATE INDEX idx_logs_context ON logdb.logs USING GIN (context_data);

COMMENT ON TABLE logdb.logs IS '구조화된 애플리케이션 로그';
COMMENT ON COLUMN logdb.logs.log_level IS '로그 레벨 (INFO, WARNING, ERROR, DEBUG)';
COMMENT ON COLUMN logdb.logs.stage_name IS '실행 중인 스테이지';
COMMENT ON COLUMN logdb.logs.agent_name IS '실행 중인 에이전트';
COMMENT ON COLUMN logdb.logs.duration_ms IS '작업 수행 시간 (밀리초)';

-- ------------------------------------------------------------
-- 2. error_logs: 에러 로그 (빠른 조회용)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logdb.error_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context_data JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_error_logs_timestamp ON logdb.error_logs(timestamp DESC);
CREATE INDEX idx_error_logs_type ON logdb.error_logs(error_type);
CREATE INDEX idx_error_logs_session ON logdb.error_logs(session_id);

COMMENT ON TABLE logdb.error_logs IS '에러 로그 (별도 테이블로 빠른 조회)';
COMMENT ON COLUMN logdb.error_logs.stack_trace IS 'Python traceback';

-- ------------------------------------------------------------
-- 3. performance_metrics: 성능 메트릭
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logdb.performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value REAL NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_metrics_name ON logdb.performance_metrics(metric_name, timestamp DESC);
CREATE INDEX idx_metrics_timestamp ON logdb.performance_metrics(timestamp DESC);
CREATE INDEX idx_metrics_tags ON logdb.performance_metrics USING GIN (tags);

COMMENT ON TABLE logdb.performance_metrics IS '성능 메트릭 (응답 시간, 캐시 히트율 등)';
COMMENT ON COLUMN logdb.performance_metrics.metric_name IS '메트릭 이름 (api_response_time, cache_hit_rate 등)';
COMMENT ON COLUMN logdb.performance_metrics.tags IS 'JSON 형식의 태그 (환경, 버전 등)';

-- ============================================================
-- 초기 데이터 및 설정
-- ============================================================

-- 기본 인덱스 통계 업데이트
ANALYZE statedb.sessions;
ANALYZE statedb.user_inputs;
ANALYZE statedb.dialogues;
ANALYZE logdb.logs;

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'KIME Chat Database Schema Initialized Successfully!';
    RAISE NOTICE 'StateDB: 8 tables created';
    RAISE NOTICE 'LogDB: 3 tables created';
    RAISE NOTICE '============================================================';
END $$;
