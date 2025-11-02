-- ========================================
-- 8️⃣ AI 에이전트 성능 분석
-- ========================================
-- 용도: 각 AI 에이전트의 실행 시간 통계 분석
-- 실행 시점: 기술적 상세 설명 시

SELECT
    agent_name,
    COUNT(*) as call_count,
    ROUND(AVG(execution_time_ms), 2) as avg_time_ms,
    ROUND(MIN(execution_time_ms), 2) as min_time_ms,
    ROUND(MAX(execution_time_ms), 2) as max_time_ms,
    COUNT(CASE WHEN llm_model IS NOT NULL THEN 1 END) as llm_calls
FROM statedb.training_logs
WHERE session_id = '여기에_세션_ID_붙여넣기'
GROUP BY agent_name
ORDER BY avg_time_ms DESC;

-- ✅ 확인 포인트:
-- - parent_agent: 가장 느림 (평균 5000-8000ms) → LLM 호출
-- - router: 중간 (평균 2000-4000ms) → 의도 분석
-- - guardrail: 중간 (평균 2000-3000ms) → 입력 검증
-- - children_agent: 빠름 (평균 1000-2000ms) → 대화 생성
-- - dialogue_agent: 매우 빠름 (평균 0.1ms) → 형식 정리만

-- 💡 설명 포인트:
-- "parent_agent가 가장 느린 이유는 LLM을 호출하기 때문입니다"
-- "dialogue_agent는 단순 형식 정리라서 0.1ms로 매우 빠릅니다"
-- "전체 응답 시간은 약 10-20초이며, 대부분 LLM API 호출 시간입니다"
