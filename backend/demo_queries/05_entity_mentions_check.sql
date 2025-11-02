-- ========================================
-- 5️⃣ 엔티티 멘션 상세 확인
-- ========================================
-- 용도: 엔티티가 어떤 문맥에서 언급되었는지 상세 추적
-- 실행 시점: 엔티티 확인 후

SELECT
    e.name as entity_name,
    e.entity_type,
    em.turn_number,
    LEFT(em.context_snippet, 60) as context,
    em.sentiment,
    em.timestamp
FROM statedb.entity_mentions em
JOIN statedb.entities e ON em.entity_id = e.id
WHERE em.session_id = '여기에_세션_ID_붙여넣기'
ORDER BY em.turn_number, e.name;

-- ✅ 확인 포인트:
-- - 각 엔티티가 어느 턴에서 언급되었는지
-- - context_snippet: 어떤 문맥에서 언급되었는지
-- - sentiment: positive, neutral, negative (감정 분석)

-- 💡 TIP: 같은 엔티티가 여러 턴에서 언급되면 여러 행으로 표시됩니다
