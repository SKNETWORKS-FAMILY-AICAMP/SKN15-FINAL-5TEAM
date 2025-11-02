-- ========================================
-- 9️⃣ 사용자 장기 기억 (Vector 임베딩)
-- ========================================
-- 용도: Vector 임베딩을 활용한 장기 기억 시스템 설명
-- 실행 시점: 고급 기능 설명 시 (선택사항)

SELECT
    memory_key,
    LEFT(memory_value, 60) as memory_value_preview,
    memory_type,
    importance,
    tags,
    CASE
        WHEN embedding IS NOT NULL THEN '✅ 임베딩 있음 (1536차원)'
        ELSE '❌ 임베딩 없음'
    END as embedding_status,
    created_at
FROM statedb.user_memories
ORDER BY importance DESC, created_at DESC
LIMIT 10;

-- ✅ 확인 포인트:
-- - memory_key: 기억의 키 (예: "favorite_character")
-- - memory_value: 기억의 내용 (예: "렌고쿠를 좋아함")
-- - memory_type: character_preference, game_progress 등
-- - importance: 0.0 ~ 1.0 (중요도)
-- - embedding: pgvector (1536차원 벡터)

-- 💡 설명 포인트:
-- "이 시스템은 OpenAI의 text-embedding-3-small 모델을 사용합니다"
-- "1536차원 벡터로 의미를 저장하여, 유사한 기억을 검색할 수 있습니다"
-- "예: '불의 호흡'을 검색하면 '히노카미 카구라'도 함께 찾아집니다"

-- 🎯 추가 쿼리: Vector 유사도 검색 예시
-- SELECT
--     memory_key,
--     memory_value,
--     embedding <=> '[검색할_임베딩_벡터]'::vector AS distance
-- FROM statedb.user_memories
-- WHERE user_id = 'test'
--   AND embedding IS NOT NULL
-- ORDER BY embedding <=> '[검색할_임베딩_벡터]'::vector
-- LIMIT 5;
