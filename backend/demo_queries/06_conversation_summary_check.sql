-- ========================================
-- 6️⃣ 대화 요약 자동 생성 확인 ⭐ (핵심!)
-- ========================================
-- 용도: 10턴마다 자동으로 생성되는 대화 요약 확인
-- 실행 시점: 10번째 채팅 후 (Turn 11+)

SELECT
    session_id,
    turn_count,
    summary_turn_count,
    LENGTH(conversation_summary) as summary_length,
    conversation_summary,
    updated_at
FROM statedb.sessions
WHERE session_id = '여기에_세션_ID_붙여넣기';

-- ✅ 확인 포인트:
-- - turn_count: 현재 턴 수 (11, 13, 15...)
-- - summary_turn_count: 마지막 요약 생성 턴 (11, 21, 31...)
-- - summary_length: 요약 길이 (400-600자)
-- - conversation_summary: 전체 요약 내용
--   * 현재 스테이지
--   * 주요 캐릭터
--   * 주요 대화 내용
--   * 캐릭터 관계
--   * 게임 목표

-- 💡 데모 하이라이트:
-- "이제 10번째 대화를 입력했습니다!"
-- "이 쿼리를 실행하면..."
-- "보세요! 지금까지의 대화가 자동으로 요약되었습니다!"
-- "LLM이 주요 이벤트, 캐릭터 관계, 게임 목표를 모두 파악했네요!"

-- 🎯 예상 결과:
-- turn_count: 11 또는 13
-- summary_turn_count: 11 (Turn 11에서 생성)
-- summary_length: 441자
-- conversation_summary: "현재 스테이지는 TRAIN_PRELUDE이며, 주요 캐릭터는..."
