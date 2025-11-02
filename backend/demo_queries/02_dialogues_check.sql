-- ========================================
-- 2️⃣ 대화 저장 확인
-- ========================================
-- 용도: 사용자 입력과 AI 응답이 모두 저장되었는지 확인
-- 실행 시점: 채팅 3번 후

-- ⚠️ 세션 ID를 여기에 입력하세요
-- 위의 01_session_check.sql에서 복사한 session_id
SELECT
    turn_number,
    speaker,
    LEFT(content, 80) as content_preview,
    emotion,
    emotion_intensity,
    order_index,
    TO_CHAR(timestamp, 'HH24:MI:SS') as time
FROM statedb.dialogues
WHERE session_id = '여기에_세션_ID_붙여넣기'
ORDER BY turn_number, order_index;

-- ✅ 확인 포인트:
-- - Turn 1: user → "안녕하세요"
-- - Turn 1: tanjiro/rengoku → AI 응답
-- - Turn 3: user → "무한열차에 대해..."
-- - Turn 3: narr → 나레이션
-- - Turn 3: rengoku → 렌고쿠 대사
-- - 감정(emotion): calm, serious, tense 등
-- - 감정 강도: 0.5 ~ 0.8

-- 💡 TIP: speaker가 'user'가 아닌 것들이 AI 응답입니다
