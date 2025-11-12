-- Phase 8: Performance Optimization Indexes
-- 대화 조회 성능 향상을 위한 인덱스 추가

-- ============================================================
-- conversation.dialogues 테이블 인덱스
-- ============================================================

-- 세션별 대화 조회 (가장 빈번한 쿼리)
CREATE INDEX IF NOT EXISTS idx_dialogues_session_id
ON conversation.dialogues(session_id);

-- 세션별 최신 대화 조회 (created_at 내림차순)
CREATE INDEX IF NOT EXISTS idx_dialogues_session_created
ON conversation.dialogues(session_id, "timestamp" DESC);

-- 사용자별 대화 조회
CREATE INDEX IF NOT EXISTS idx_dialogues_speaker
ON conversation.dialogues(speaker);

-- 턴 번호 기반 조회
CREATE INDEX IF NOT EXISTS idx_dialogues_turn_number
ON conversation.dialogues(session_id, turn_number);

-- ============================================================
-- conversation.sessions 테이블 인덱스
-- ============================================================

-- 사용자별 활성 세션 조회
CREATE INDEX IF NOT EXISTS idx_sessions_user_active
ON conversation.sessions(user_id, is_active)
WHERE is_active = TRUE;

-- 시나리오별 세션 조회
CREATE INDEX IF NOT EXISTS idx_sessions_scenario
ON conversation.sessions(scenario_id);

-- 최근 세션 조회
CREATE INDEX IF NOT EXISTS idx_sessions_last_interaction
ON conversation.sessions(last_interaction_at DESC);

-- ============================================================
-- conversation.user_inputs 테이블 인덱스
-- ============================================================

-- 세션별 사용자 입력 조회
CREATE INDEX IF NOT EXISTS idx_user_inputs_session
ON conversation.user_inputs(session_id);

-- 사용자별 입력 내역 조회
CREATE INDEX IF NOT EXISTS idx_user_inputs_user_timestamp
ON conversation.user_inputs(user_id, created_at DESC);

-- ============================================================
-- 복합 인덱스 (자주 함께 사용되는 조건)
-- ============================================================

-- 사용자 + 시나리오별 대화 조회
CREATE INDEX IF NOT EXISTS idx_dialogues_speaker_timestamp
ON conversation.dialogues(speaker, "timestamp" DESC);

-- ============================================================
-- JSONB 인덱스 (chat_sessions의 state 필드)
-- ============================================================

-- state 내 특정 필드 조회 최적화 (GIN 인덱스)
CREATE INDEX IF NOT EXISTS idx_chat_sessions_state_gin
ON conversation.chat_sessions USING gin(state);

-- 자주 조회되는 state 필드에 대한 인덱스
CREATE INDEX IF NOT EXISTS idx_chat_sessions_state_scenario
ON conversation.chat_sessions((state->>'scenario_id'));

CREATE INDEX IF NOT EXISTS idx_chat_sessions_state_stage
ON conversation.chat_sessions((state->>'current_stage'));

-- ============================================================
-- 벡터 임베딩 인덱스 (향후 semantic search용)
-- ============================================================

-- pgvector IVFFlat 인덱스 (빠른 근사 검색)
-- 임베딩 기반 대화 검색 시 사용
CREATE INDEX IF NOT EXISTS idx_dialogues_embedding_ivfflat
ON conversation.dialogues
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================================
-- 통계 정보 업데이트
-- ============================================================

-- PostgreSQL 쿼리 플래너가 인덱스를 올바르게 사용하도록 통계 수집
ANALYZE conversation.dialogues;
ANALYZE conversation.sessions;
ANALYZE conversation.user_inputs;
ANALYZE conversation.chat_sessions;

-- ============================================================
-- 인덱스 성능 모니터링 쿼리 (참고용)
-- ============================================================

-- 인덱스 사용률 확인:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'conversation'
-- ORDER BY idx_scan DESC;

-- 인덱스 크기 확인:
-- SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid)) as size
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'conversation'
-- ORDER BY pg_relation_size(indexrelid) DESC;
