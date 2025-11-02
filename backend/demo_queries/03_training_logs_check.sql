-- ========================================
-- 3️⃣ AI 학습 로그 확인
-- ========================================
-- 용도: AI 에이전트의 실행 기록과 성능 메트릭 확인
-- 실행 시점: 채팅 3번 후

SELECT
    turn_number,
    agent_name,
    stage_type,
    intent,
    LEFT(user_input, 40) as user_input_preview,
    execution_time_ms,
    llm_model,
    TO_CHAR(timestamp, 'HH24:MI:SS') as time
FROM statedb.training_logs
WHERE session_id = '여기에_세션_ID_붙여넣기'
ORDER BY turn_number DESC, timestamp DESC
LIMIT 20;

-- ✅ 확인 포인트:
-- - guardrail: 입력 검증 (2000-3000ms)
-- - router: 의도 분석 (2000-4000ms)
-- - parent_agent: 메인 로직 (5000-8000ms)
-- - children_agent: 대화 생성 (1000-2000ms)
-- - dialogue_agent: 형식 정리 (0.1ms - 매우 빠름!)

-- 💡 TIP: execution_time_ms가 긴 것은 LLM을 호출한 것입니다
