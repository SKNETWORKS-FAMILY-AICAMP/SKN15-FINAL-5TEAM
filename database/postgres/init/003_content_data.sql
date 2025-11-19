-- ============================================================================
-- 003: Complete Game Content Data Migration from JSON
-- ============================================================================
-- JSON 파일의 모든 데이터를 데이터베이스로 완전 마이그레이션
-- ============================================================================

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

-- ============================================================================
-- Insert Rank Definitions (귀살대 계급 체계)
-- ============================================================================

INSERT INTO content.rank_definitions (
    rank_code, rank_name_ko, rank_name_en, rank_name_ja,
    min_xp, level_range_start, level_range_end,
    icon_emoji, description_ko
)
VALUES
    ('MIZUNOTO', '계급 계(癸)', 'Mizunoto', '癸', 0, 1, 10, '🌱', '귀살대 입문자. 최하위 계급'),
    ('MIZUNOE', '계급 임(壬)', 'Mizunoe', '壬', 100, 11, 20, '🌿', '기초를 다진 초심자'),
    ('KANOTO', '계급 신(辛)', 'Kanoto', '辛', 300, 21, 30, '🪴', '실전 경험을 쌓아가는 단계'),
    ('KANOE', '계급 경(庚)', 'Kanoe', '庚', 600, 31, 40, '🌳', '어느 정도 실력을 인정받은 대원'),
    ('TSUCHINOTO', '계급 기(己)', 'Tsuchinoto', '己', 1000, 41, 50, '⚔️', '중견 귀살대원'),
    ('TSUCHINOE', '계급 무(戊)', 'Tsuchinoe', '戊', 1500, 51, 60, '🗡️', '숙련된 전사'),
    ('HINOTO', '계급 정(丁)', 'Hinoto', '丁', 2200, 61, 70, '💫', '뛰어난 실력자'),
    ('HINOE', '계급 병(丙)', 'Hinoe', '丙', 3000, 71, 80, '✨', '주급 후보'),
    ('KINOTO', '계급 을(乙)', 'Kinoto', '乙', 4000, 81, 90, '⭐', '최상급 대원'),
    ('KINOE', '계급 갑(甲)', 'Kinoe', '甲', 5500, 91, 100, '🌟', '주(柱)에 준하는 실력'),
    ('HASHIRA', '주(柱)', 'Hashira', '柱', 10000, 101, 999, '👑', '귀살대 최강의 9인')
ON CONFLICT (rank_code) DO NOTHING;

-- ============================================================================
-- Insert all scenarios with complete metadata
-- ============================================================================

INSERT INTO content.scenarios (
    scenario_id, title, emoji, description, detail_description,
    image_url, thumbnail_url, implemented, category, mood, tags,
    likes, comments, views, route_path, is_active, display_order,
    created_at, updated_at
)
VALUES
    -- ending (엔딩 이후)
    (
        'ending',
        '엔딩 이후',
        '🌸',
        '최종 결전 후 동료들과 함께하는 평범하지만 소중한 일상',
        '탄지로, 젠이츠, 이노스케와 함께 마을 순찰과 훈련을 하며 서로를 돌보는 따뜻한 이야기',
        '/images/엔딩이후.png',
        '/images/엔딩이후.png',
        true,
        '일상 · 힐링 · 로맨스',
        ARRAY['평화로운', '따뜻함', '감성적'],
        ARRAY['#엔딩이후', '#일상', '#평화', '#동료애'],
        87,
        28,
        720,
        '/chat/ending',
        true,
        1,
        NOW(),
        NOW()
    ),
    -- infinity-castle (무한성)
    (
        'infinity-castle',
        '무한성',
        '🏯',
        '무한성에서 펼쳐지는 최종 결전',
        '무잔과의 최종 대결을 앞두고 무한성에 갇힌 귀살대원들. 상현들과의 치열한 전투, 그리고 모두의 운명이 결정되는 순간',
        '/images/무한성.webp',
        '/images/무한성.webp',
        false,
        '액션 · 전투 · 긴장감',
        ARRAY['긴박함', '스릴', '진지함'],
        ARRAY['#최종결전', '#귀살대', '#무잔전'],
        156,
        67,
        1850,
        '/chat/infinity-castle',
        true,
        2,
        NOW(),
        NOW()
    ),
    -- tanjiro (편의점 탄지로)
    (
        'tanjiro',
        '편의점 탄지로',
        '🏪',
        '편의점에서 일하는 탄지로와의 일상 대화',
        '현대 배경 AU. 편의점 알바생 탄지로와 함께하는 따뜻하고 편안한 일상',
        '/images/편의점탄지로.png',
        '/images/편의점탄지로.png',
        false,
        '일상 · 힐링 · 현대AU',
        ARRAY['편안함', '따뜻함', '친근함'],
        ARRAY['#편의점', '#일상', '#탄지로'],
        121,
        45,
        1200,
        '/chat/tanjiro',
        true,
        3,
        NOW(),
        NOW()
    ),
    -- counseling (귀칼 상담소 AU)
    (
        'counseling',
        '귀칼 상담소 AU',
        '💬',
        '귀살대원들이 운영하는 고민상담소',
        'AU 세계관. 탄지로와 동료들이 여러분의 고민을 들어드립니다. 따뜻한 위로와 진심 어린 조언을 나눠보세요',
        '/images/귀칼상담소.png',
        '/images/귀칼상담소.png',
        false,
        '힐링 · 상담 · 감성',
        ARRAY['위로', '공감', '따뜻함'],
        ARRAY['#상담소', '#힐링AU', '#감정공감'],
        134,
        52,
        1150,
        '/chat/counseling',
        true,
        4,
        NOW(),
        NOW()
    ),
    -- idol (아이돌/밴드 AU)
    (
        'idol',
        '아이돌/밴드 AU',
        '🎸',
        '아이돌 또는 밴드로 활동하는 캐릭터들',
        'AU 세계관. 귀살대원들이 아이돌 그룹 또는 밴드로 데뷔! 당신은 귀살대원의 매니저입니다.
        화려한 무대 위에서 펼쳐지는 그들의 이야기를 가장 가까이서 지켜봐주세요',
        '/images/아이돌밴드.png',
        '/images/아이돌밴드.png',
        false,
        '엔터테인먼트 · 음악 · 팬심',
        ARRAY['흥겨움', '열정', '설렘'],
        ARRAY['#아이돌AU', '#밴드AU', '#팬심폭발'],
        203,
        89,
        2100,
        '/chat/idol_band',
        true,
        5,
        NOW(),
        NOW()
    ),
    -- cutscene5_llm_driven (무한열차)
    (
        'cutscene5_llm_driven',
        '무한열차',
        '🚂',
        '무한열차에서 펼쳐지는 치열한 전투와 동료애',
        '열차 안에서 벌어지는 악몽과 현실의 경계. 엔무와의 대결, 그리고 상현의 삼(參)과의 조우까지. 탄지로와 동료들이 승객들을 지키기 위해 싸우는 이야기',
        '/images/무한열차.jpeg',
        '/images/무한열차.jpeg',
        true,
        '액션 · 감동',
        ARRAY['역동적', '긴박함', '감동적'],
        ARRAY['#무한열차', '#아카자', '#엔무'],
        98,
        32,
        890,
        '/chat/cutscene5_llm_driven',
        true,
        6,
        NOW(),
        NOW()
    ),
    -- train (무한열차편 - 기존 데이터와 호환)
    (
        'train',
        '무한열차편',
        '🚂',
        '탄지로와 렌고쿠가 무한열차에서 겪는 모험',
        '렌고쿠와 함께하는 무한열차 임무',
        '/images/무한열차.jpeg',
        '/images/무한열차.jpeg',
        true,
        '액션 · 감동',
        ARRAY['역동적', '긴박함'],
        ARRAY['#무한열차', '#렌고쿠', '#액션'],
        98,
        32,
        890,
        '/chat/train',
        true,
        7,
        NOW(),
        NOW()
    )
ON CONFLICT (scenario_id) DO UPDATE SET
    emoji = EXCLUDED.emoji,
    detail_description = EXCLUDED.detail_description,
    image_url = EXCLUDED.image_url,
    thumbnail_url = EXCLUDED.thumbnail_url,
    implemented = EXCLUDED.implemented,
    category = EXCLUDED.category,
    mood = EXCLUDED.mood,
    tags = EXCLUDED.tags,
    likes = EXCLUDED.likes,
    comments = EXCLUDED.comments,
    views = EXCLUDED.views,
    route_path = EXCLUDED.route_path,
    updated_at = NOW();

-- ============================================================================
-- Insert scenario characters (시나리오별 등장 캐릭터)
-- ============================================================================

INSERT INTO content.scenario_characters (scenario_id, character_name, character_image, greeting, status, color, display_order)
VALUES
    -- ending 캐릭터
    ('ending', '탄지로', '/images/프로필_탄지로.png', '안녕하세요! 함께 평화로운 시간을 보내세요.', '대화 가능', 'bg-orange-100', 1),
    ('ending', '네즈코', '/images/프로필_네즈코.png', '흠흠~ 오늘도 좋은 하루 보내세요!', '여동생', 'bg-pink-100', 2),
    ('ending', '젠이츠', '/images/프로필_젠이츠.png', '우와! 정말 즐거운 시간이 될 것 같아요!', '동기', 'bg-yellow-100', 3),
    ('ending', '이노스케', '/images/프로필_이노스케.png', '이야! 재미있는 모험을 시작해보자구!', '동기', 'bg-green-100', 4),

    -- infinity-castle 캐릭터
    ('infinity-castle', '탄지로', '/images/프로필_탄지로.png', '모두를 지키기 위해 최선을 다하겠습니다!', '대화 가능', 'bg-orange-100', 1),
    ('infinity-castle', '기유', '/images/프로필_기유.png', '함께 싸우자.', '대화 가능', 'bg-blue-100', 2),
    ('infinity-castle', '시노부', '/images/프로필_시노부.png', '부디 조심하세요.', '대화 가능', 'bg-purple-100', 3),
    ('infinity-castle', '렌고쿠', '/images/프로필_렌고쿠.png', '마음을 불태워라!', '대화 가능', 'bg-red-100', 4),

    -- tanjiro 캐릭터
    ('tanjiro', '탄지로', '/images/프로필_탄지로.png', '어서오세요! 무엇을 도와드릴까요?', '대화 가능', 'bg-orange-100', 1),

    -- counseling 캐릭터
    ('counseling', '탄지로', '/images/프로필_탄지로.png', '편하게 말씀해주세요. 함께 고민을 나눠봐요.', '대화 가능', 'bg-orange-100', 1),

    -- idol 캐릭터
    ('idol', '탄지로', '/images/프로필_탄지로.png', '여러분의 응원이 제게 큰 힘이 됩니다!', '대화 가능', 'bg-orange-100', 1),

    -- cutscene5_llm_driven 캐릭터
    ('cutscene5_llm_driven', '탄지로', '/images/프로필_탄지로.png', '안녕하세요! 함께 평화로운 시간을 보내세요.', '대화 가능', 'bg-orange-100', 1),
    ('cutscene5_llm_driven', '렌고쿠', '/images/프로필_렌고쿠.png', '불같은 열정으로 함께하겠습니다!', '대화 가능', 'bg-red-100', 2),
    ('cutscene5_llm_driven', '젠이츠', '/images/프로필_젠이츠.png', '우와! 정말 즐거운 시간이 될 것 같아요!', '대화 가능', 'bg-yellow-100', 3),
    ('cutscene5_llm_driven', '이노스케', '/images/프로필_이노스케.png', '이야! 재미있는 모험을 시작해보자구!', '대화 가능', 'bg-green-100', 4)
ON CONFLICT (scenario_id, character_name) DO NOTHING;

-- ============================================================================
-- Verification and Summary
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ Complete JSON Data Migration Finished!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Scenarios migrated: % rows', (SELECT COUNT(*) FROM content.scenarios);
    RAISE NOTICE 'Scenario characters migrated: % rows', (SELECT COUNT(*) FROM content.scenario_characters);
    RAISE NOTICE '';
    RAISE NOTICE 'All data from scenarios.json has been migrated to database.';
    RAISE NOTICE 'Images, tags, metadata, and character info are all included.';
    RAISE NOTICE '============================================================';
END $$;

-- ============================================================================
-- Legacy scenario beats and goals data (from train scenario)
-- ============================================================================

INSERT INTO content.scenario_beats VALUES ('train:beats_rengoku_dialogue', 'train', 'beats_rengoku_dialogue', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_enmu_appear', 'train', 'beats_enmu_appear', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_enmu_real_battle', 'train', 'beats_enmu_real_battle', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_UpperMoons3_appeared', 'train', 'beats_UpperMoons3_appeared', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_route', 'train', 'beats_route', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_intervene_hint', 'train', 'beats_intervene_hint', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_smell', 'train', 'beats_smell', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:zenitsu_scene', 'train', 'zenitsu_scene', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_feedback_success_zenitsu', 'train', 'beats_feedback_success_zenitsu', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_feedback_fail_zenitsu', 'train', 'beats_feedback_fail_zenitsu', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_return_to_front', 'train', 'beats_return_to_front', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:inosuke_scene', 'train', 'inosuke_scene', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_feedback_success_inosuke', 'train', 'beats_feedback_success_inosuke', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_feedback_fail_inosuke', 'train', 'beats_feedback_fail_inosuke', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_feedback_fail_zenitsu_end', 'train', 'beats_feedback_fail_zenitsu_end', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_feedback_fail_inosuke_end', 'train', 'beats_feedback_fail_inosuke_end', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_reckless_sacrifice', 'train', 'beats_reckless_sacrifice', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_boss_exit_hidden', 'train', 'beats_boss_exit_hidden', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;
INSERT INTO content.scenario_beats VALUES ('train:beats_boss_exit_basic', 'train', 'beats_boss_exit_basic', NULL, 0, NULL, NOW()) ON CONFLICT (beat_id) DO NOTHING;

-- Note: beat_goals data continues in the legacy backup file if needed
