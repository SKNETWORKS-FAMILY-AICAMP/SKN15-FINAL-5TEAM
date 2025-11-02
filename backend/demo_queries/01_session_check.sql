-- ========================================
-- 1️⃣ 세션 생성 확인
-- ========================================
-- 용도: 새로운 세션이 생성되었는지 확인
-- 실행 시점: 첫 번째 채팅 후

SELECT
    session_id,
    user_id,
    scenario_id,
    turn_count,
    stage,
    created_at,
    updated_at
FROM statedb.sessions
ORDER BY created_at DESC
LIMIT 1;

-- ✅ 확인 포인트:
-- - session_id: 새로운 UUID 생성됨
-- - turn_count: 1 (첫 채팅)
-- - scenario_id: train 또는 cutscene5_llm_driven
-- - created_at: 방금 전 시간
