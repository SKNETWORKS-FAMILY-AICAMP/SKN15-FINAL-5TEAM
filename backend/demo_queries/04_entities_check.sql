-- ========================================
-- 4️⃣ 엔티티 자동 추출 확인
-- ========================================
-- 용도: NLP 기반으로 자동 추출된 엔티티 확인
-- 실행 시점: "아카자", "불의 호흡" 등을 언급한 후

SELECT
    e.id,
    e.name,
    e.entity_type,
    e.first_mentioned_turn,
    e.description,
    COUNT(em.id) as mention_count
FROM statedb.entities e
LEFT JOIN statedb.entity_mentions em ON e.id = em.entity_id
WHERE e.session_id = '여기에_세션_ID_붙여넣기'
GROUP BY e.id, e.name, e.entity_type, e.first_mentioned_turn, e.description
ORDER BY mention_count DESC, e.first_mentioned_turn;

-- ✅ 확인 포인트:
-- - 아카자 (character): 처음 언급된 턴과 언급 횟수
-- - 불의 호흡 (skill): 처음 언급된 턴과 언급 횟수
-- - 렌고쿠 (character): 처음 언급된 턴과 언급 횟수
-- - entity_type: character, skill, location, item 등

-- 💡 TIP: mention_count가 높을수록 대화에서 자주 언급된 중요 엔티티입니다
