-- Insert test sessions and dialogues for testing recent chats feature
-- User: zenitsu (4434cfa1-d255-4137-b952-08f0be5af270)

-- Session 1: 무한열차 (train) - Most recent
INSERT INTO statedb.sessions (
    session_id,
    scenario_id,
    user_id,
    current_stage,
    turn_count,
    conversation_summary,
    created_at,
    updated_at
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    'train',
    '4434cfa1-d255-4137-b952-08f0be5af270',
    'mission',
    8,
    '렌고쿠와 함께 무한열차에서 귀신을 토벌하는 임무 수행 중',
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '30 minutes'
);

-- Dialogues for Session 1
INSERT INTO statedb.dialogues (session_id, turn_number, speaker, content, emotion, emotion_intensity, order_index, timestamp) VALUES
('11111111-1111-1111-1111-111111111111', 1, 'user', '렌고쿠님, 무한열차에서 이상한 기운이 느껴져요.', NULL, NULL, 0, NOW() - INTERVAL '2 hours'),
('11111111-1111-1111-1111-111111111111', 1, '렌고쿠', '잘 알아차렸구나! 나도 느꼈다. 이 열차 안에는 분명 귀신이 숨어있다!', 'excited', 'high', 1, NOW() - INTERVAL '2 hours'),
('11111111-1111-1111-1111-111111111111', 2, 'user', '어떻게 대처하면 좋을까요?', NULL, NULL, 0, NOW() - INTERVAL '1 hour 50 minutes'),
('11111111-1111-1111-1111-111111111111', 2, '렌고쿠', '우무! 먼저 승객들을 안전하게 대피시키는 것이 최우선이다! 함께 움직이자!', 'determined', 'high', 1, NOW() - INTERVAL '1 hour 50 minutes'),
('11111111-1111-1111-1111-111111111111', 3, 'user', '알겠습니다! 제가 뒤쪽 객차를 담당하겠습니다.', NULL, NULL, 0, NOW() - INTERVAL '1 hour 30 minutes'),
('11111111-1111-1111-1111-111111111111', 3, '렌고쿠', '좋아! 위험하면 즉시 내게 알려라. 네 안전이 가장 중요하다!', 'concerned', 'medium', 1, NOW() - INTERVAL '1 hour 30 minutes'),
('11111111-1111-1111-1111-111111111111', 4, 'user', '뒤쪽 객차에서 귀신을 발견했어요!', NULL, NULL, 0, NOW() - INTERVAL '1 hour'),
('11111111-1111-1111-1111-111111111111', 4, '렌고쿠', '훌륭하다! 내가 지금 간다! 염의 호흡으로 한 번에 처리하겠다!', 'fierce', 'very_high', 1, NOW() - INTERVAL '30 minutes');

-- Session 2: 편의점 탄지로 (tanjiro) - 2nd most recent
INSERT INTO statedb.sessions (
    session_id,
    scenario_id,
    user_id,
    current_stage,
    turn_count,
    conversation_summary,
    created_at,
    updated_at
) VALUES (
    '22222222-2222-2222-2222-222222222222',
    'tanjiro',
    '4434cfa1-d255-4137-b952-08f0be5af270',
    'dialogue',
    6,
    '편의점 알바 탄지로와 심야 대화를 나누는 중',
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '18 hours'
);

-- Dialogues for Session 2
INSERT INTO statedb.dialogues (session_id, turn_number, speaker, content, emotion, emotion_intensity, order_index, timestamp) VALUES
('22222222-2222-2222-2222-222222222222', 1, 'user', '탄지로, 오늘 손님 많았어?', NULL, NULL, 0, NOW() - INTERVAL '1 day'),
('22222222-2222-2222-2222-222222222222', 1, '탄지로', '응, 오늘은 생각보다 바빴어. 하지만 모두 친절하게 대해줘서 기분이 좋았어!', 'happy', 'medium', 1, NOW() - INTERVAL '1 day'),
('22222222-2222-2222-2222-222222222222', 2, 'user', '역시 탄지로답네. 항상 긍정적이야.', NULL, NULL, 0, NOW() - INTERVAL '23 hours'),
('22222222-2222-2222-2222-222222222222', 2, '탄지로', '고마워! 넌 오늘 어땠어? 힘든 일은 없었어?', 'caring', 'medium', 1, NOW() - INTERVAL '23 hours'),
('22222222-2222-2222-2222-222222222222', 3, 'user', '조금 피곤하긴 하지만 괜찮아.', NULL, NULL, 0, NOW() - INTERVAL '20 hours'),
('22222222-2222-2222-2222-222222222222', 3, '탄지로', '무리하지 마. 내가 따뜻한 차 한 잔 줄게. 잠깐만 기다려!', 'gentle', 'medium', 1, NOW() - INTERVAL '18 hours');

-- Session 3: 무한성 (infinity-castle) - 3rd most recent
INSERT INTO statedb.sessions (
    session_id,
    scenario_id,
    user_id,
    current_stage,
    turn_count,
    conversation_summary,
    created_at,
    updated_at
) VALUES (
    '33333333-3333-3333-3333-333333333333',
    'infinity-castle',
    '4434cfa1-d255-4137-b952-08f0be5af270',
    'battle',
    10,
    '무한성에서 상현 귀신과 전투 중',
    NOW() - INTERVAL '3 days',
    NOW() - INTERVAL '2 days'
);

-- Dialogues for Session 3
INSERT INTO statedb.dialogues (session_id, turn_number, speaker, content, emotion, emotion_intensity, order_index, timestamp) VALUES
('33333333-3333-3333-3333-333333333333', 1, 'user', '이곳이 무한성인가... 구조가 계속 바뀌네.', NULL, NULL, 0, NOW() - INTERVAL '3 days'),
('33333333-3333-3333-3333-333333333333', 1, '나키메', '후후... 내 혈귀술 속에서 빠져나갈 수 있을까?', 'sinister', 'high', 1, NOW() - INTERVAL '3 days'),
('33333333-3333-3333-3333-333333333333', 2, 'user', '반드시 빠져나가서 무잔을 쓰러뜨리겠어!', NULL, NULL, 0, NOW() - INTERVAL '2 days 20 hours'),
('33333333-3333-3333-3333-333333333333', 2, '나키메', '흥미롭군. 하지만 그 전에 나를 이겨야 할 텐데...', 'confident', 'medium', 1, NOW() - INTERVAL '2 days 20 hours'),
('33333333-3333-3333-3333-333333333333', 3, 'user', '호흡을 집중하고... 지금이다!', NULL, NULL, 0, NOW() - INTERVAL '2 days 15 hours'),
('33333333-3333-3333-3333-333333333333', 3, '나키메', '...! 예상보다 강하군. 하지만 이건 어떻겠나?', 'surprised', 'medium', 1, NOW() - INTERVAL '2 days');

-- Session 4: 귀칼 상담소 AU (counseling) - 4th (oldest)
INSERT INTO statedb.sessions (
    session_id,
    scenario_id,
    user_id,
    current_stage,
    turn_count,
    conversation_summary,
    created_at,
    updated_at
) VALUES (
    '44444444-4444-4444-4444-444444444444',
    'counseling',
    '4434cfa1-d255-4137-b952-08f0be5af270',
    'counseling',
    12,
    '기유 선생님과 일상 고민 상담 진행 중',
    NOW() - INTERVAL '5 days',
    NOW() - INTERVAL '4 days'
);

-- Dialogues for Session 4
INSERT INTO statedb.dialogues (session_id, turn_number, speaker, content, emotion, emotion_intensity, order_index, timestamp) VALUES
('44444444-4444-4444-4444-444444444444', 1, 'user', '기유 선생님, 상담 받으러 왔어요.', NULL, NULL, 0, NOW() - INTERVAL '5 days'),
('44444444-4444-4444-4444-444444444444', 1, '기유', '...응. 앉아. 무슨 일이야?', 'calm', 'low', 1, NOW() - INTERVAL '5 days'),
('44444444-4444-4444-4444-444444444444', 2, 'user', '요즘 친구 관계가 좀 어려워요.', NULL, NULL, 0, NOW() - INTERVAL '4 days 20 hours'),
('44444444-4444-4444-4444-444444444444', 2, '기유', '...친구는 소중하지. 어떤 점이 어렵지?', 'attentive', 'medium', 1, NOW() - INTERVAL '4 days 20 hours'),
('44444444-4444-4444-4444-444444444444', 3, 'user', '제 마음을 이해 못 해주는 것 같아서요.', NULL, NULL, 0, NOW() - INTERVAL '4 days 15 hours'),
('44444444-4444-4444-4444-444444444444', 3, '기유', '...나도 그런 적 있어. 하지만 진심으로 대화하면 분명 통할 거야.', 'empathetic', 'medium', 1, NOW() - INTERVAL '4 days');

COMMIT;
