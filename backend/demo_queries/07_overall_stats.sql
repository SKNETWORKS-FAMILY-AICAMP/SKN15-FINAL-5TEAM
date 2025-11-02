-- ========================================
-- 7️⃣ 전체 데이터 구조 한눈에 보기
-- ========================================
-- 용도: 모든 테이블의 데이터 현황을 한눈에 확인
-- 실행 시점: 데모 종료 시 전체 요약용

SELECT
    'Sessions' as table_name,
    COUNT(*) as count,
    '게임 세션 (유저별 플레이 기록)' as description
FROM statedb.sessions
UNION ALL
SELECT
    'Dialogues',
    COUNT(*),
    '대화 내역 (유저 입력 + AI 응답)'
FROM statedb.dialogues
UNION ALL
SELECT
    'Training Logs',
    COUNT(*),
    'AI 학습 로그 (에이전트 실행 기록)'
FROM statedb.training_logs
UNION ALL
SELECT
    'Entities',
    COUNT(*),
    '추출된 엔티티 (캐릭터, 스킬, 장소 등)'
FROM statedb.entities
UNION ALL
SELECT
    'Entity Mentions',
    COUNT(*),
    '엔티티 언급 기록 (문맥 추적)'
FROM statedb.entity_mentions
UNION ALL
SELECT
    'User Memories',
    COUNT(*),
    '장기 기억 (Vector 임베딩)'
FROM statedb.user_memories
UNION ALL
SELECT
    'Affinity Records',
    COUNT(*),
    '캐릭터 친밀도 변화'
FROM statedb.affinity_records
UNION ALL
SELECT
    'Entity Relationships',
    COUNT(*),
    '엔티티 간 관계 (Graph RAG)'
FROM statedb.entity_relationships
ORDER BY count DESC;

-- ✅ 확인 포인트:
-- - Dialogues가 가장 많음 (모든 대화 저장)
-- - Training Logs가 그 다음 (각 에이전트마다 로그)
-- - Entities와 Entity Mentions (자동 추출)
-- - User Memories (장기 기억)

-- 💡 데모 마무리 멘트:
-- "보시는 것처럼 한 번의 대화로 8개 테이블에 데이터가 저장되었습니다!"
-- "이 모든 것이 자동으로 수집되어, AI 학습과 개인화에 활용됩니다!"
