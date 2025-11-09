-- ============================================================
-- 012_user_progression.sql
-- 사용자 진행도(Progression) 및 장비 시스템
--
-- 목적:
--   - 사용자별 계급(rank), 레벨, 경험치 추적
--   - 채팅 통계 (메시지 수, 세션 수, 플레이 시간)
--   - 장비 상태 (일륜도, 복장, 까마귀)
--
-- 생성일: 2025-11-02
-- ============================================================

-- ============================================================
-- 1. Rank Definitions (계급 정의)
-- ============================================================

CREATE TABLE IF NOT EXISTS statedb.rank_definitions (
    rank_code VARCHAR(50) PRIMARY KEY,
    rank_name_ko VARCHAR(100) NOT NULL,
    rank_name_en VARCHAR(100),
    rank_name_ja VARCHAR(100),
    min_xp INTEGER NOT NULL,
    level_range_start INTEGER NOT NULL,
    level_range_end INTEGER NOT NULL,
    icon_emoji VARCHAR(10),
    description_ko TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE statedb.rank_definitions IS '계급 정의 (견습생 → 대원 → 정예 → 주 후보 → 주)';
COMMENT ON COLUMN statedb.rank_definitions.rank_code IS '계급 코드 (예: novice, member, hashira)';
COMMENT ON COLUMN statedb.rank_definitions.min_xp IS '해당 계급 도달에 필요한 최소 경험치';

-- 초기 계급 데이터 삽입 (귀멸의 칼날 4단계 계급 체계)
INSERT INTO statedb.rank_definitions (rank_code, rank_name_ko, rank_name_en, rank_name_ja, min_xp, level_range_start, level_range_end, icon_emoji, description_ko)
VALUES
    ('member', '평대원', 'Demon Slayer Corps Member', '鬼殺隊隊士', 0, 1, 20, '⚔️', '귀살대 일반 대원'),
    ('elite', '정예 대원', 'Elite Slayer', '精鋭隊士', 2000, 21, 40, '🏅', '뛰어난 실력을 인정받은 정예 대원'),
    ('pillar_candidate', '주 후보', 'Pillar Candidate', '柱候補', 8000, 41, 60, '🌟', '주(柱)에 준하는 실력을 갖춘 강자'),
    ('hashira', '주 (柱)', 'Hashira (Pillar)', '柱', 20000, 61, 99, '💎', '귀살대 최강의 9명, 각 호흡의 정점')
ON CONFLICT (rank_code) DO NOTHING;

-- ============================================================
-- 2. User Progression (사용자 진행도)
-- ============================================================

CREATE TABLE IF NOT EXISTS statedb.user_progression (
    user_id UUID PRIMARY KEY REFERENCES statedb.users(user_id) ON DELETE CASCADE,

    -- 계급 및 레벨
    rank_code VARCHAR(50) DEFAULT 'novice' REFERENCES statedb.rank_definitions(rank_code),
    experience_points INTEGER DEFAULT 0 CHECK (experience_points >= 0),
    level INTEGER DEFAULT 1 CHECK (level >= 1 AND level <= 99),

    -- 채팅 통계
    total_messages INTEGER DEFAULT 0 CHECK (total_messages >= 0),
    total_sessions INTEGER DEFAULT 0 CHECK (total_sessions >= 0),
    total_play_minutes INTEGER DEFAULT 0 CHECK (total_play_minutes >= 0),
    scenarios_completed INTEGER DEFAULT 0 CHECK (scenarios_completed >= 0),
    achievements_count INTEGER DEFAULT 0 CHECK (achievements_count >= 0),

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE statedb.user_progression IS '사용자별 진행도 (레벨, 경험치, 통계)';
COMMENT ON COLUMN statedb.user_progression.experience_points IS '총 획득 경험치 (XP)';
COMMENT ON COLUMN statedb.user_progression.level IS '현재 레벨 (1-99)';
COMMENT ON COLUMN statedb.user_progression.total_messages IS '전체 대화 메시지 수';
COMMENT ON COLUMN statedb.user_progression.total_sessions IS '전체 세션 수';
COMMENT ON COLUMN statedb.user_progression.total_play_minutes IS '전체 플레이 시간 (분)';

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_user_progression_xp ON statedb.user_progression(experience_points DESC);
CREATE INDEX IF NOT EXISTS idx_user_progression_level ON statedb.user_progression(level DESC);

-- ============================================================
-- 3. User Equipment (사용자 장비)
-- ============================================================

CREATE TABLE IF NOT EXISTS statedb.user_equipment (
    user_id UUID PRIMARY KEY REFERENCES statedb.users(user_id) ON DELETE CASCADE,

    -- 장비 상태
    sword_status VARCHAR(50) DEFAULT 'good' CHECK (sword_status IN ('excellent', 'good', 'fair', 'poor', 'broken')),
    uniform_status VARCHAR(50) DEFAULT 'worn' CHECK (uniform_status IN ('pristine', 'worn', 'equipped', 'damaged', 'torn')),
    crow_status VARCHAR(50) DEFAULT 'waiting' CHECK (crow_status IN ('waiting', 'active', 'resting', 'absent')),

    -- 추가 정보 (향후 확장용)
    sword_type VARCHAR(100),  -- 예: '물의 호흡', '뇌의 호흡'
    uniform_color VARCHAR(50),
    crow_name VARCHAR(100),

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE statedb.user_equipment IS '사용자 장비 상태 (일륜도, 복장, 까마귀)';
COMMENT ON COLUMN statedb.user_equipment.sword_status IS '일륜도 상태: excellent(완벽) > good(양호) > fair(보통) > poor(나쁨) > broken(파손)';
COMMENT ON COLUMN statedb.user_equipment.uniform_status IS '복장 상태: pristine(새것) > worn(착용중) > equipped(장착) > damaged(손상) > torn(찢김)';
COMMENT ON COLUMN statedb.user_equipment.crow_status IS '까마귀 상태: waiting(대기중) > active(활동중) > resting(휴식) > absent(부재중)';

-- ============================================================
-- 4. XP Transaction Log (경험치 거래 내역)
-- ============================================================

CREATE TABLE IF NOT EXISTS statedb.xp_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,

    -- 거래 정보
    xp_amount INTEGER NOT NULL,
    xp_type VARCHAR(50) NOT NULL CHECK (xp_type IN ('message', 'session_complete', 'scenario_complete', 'achievement', 'daily_bonus', 'event')),
    xp_balance_after INTEGER NOT NULL CHECK (xp_balance_after >= 0),

    -- 레벨업 정보
    level_before INTEGER,
    level_after INTEGER,
    did_level_up BOOLEAN DEFAULT FALSE,

    -- 메타데이터
    description TEXT,
    metadata JSONB,  -- 추가 정보 (예: scenario_id, achievement_id)

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE statedb.xp_transactions IS '경험치 획득 내역 (감사 로그)';
COMMENT ON COLUMN statedb.xp_transactions.xp_type IS '획득 타입: message(메시지), session_complete(세션 완료), scenario_complete(시나리오 완료), achievement(업적), daily_bonus(일일 보너스), event(이벤트)';

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_xp_transactions_user_id ON statedb.xp_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_xp_transactions_type ON statedb.xp_transactions(xp_type);

-- ============================================================
-- 5. Trigger: 신규 사용자 자동 초기화
-- ============================================================

CREATE OR REPLACE FUNCTION create_user_progression()
RETURNS TRIGGER AS $$
BEGIN
    -- user_progression 초기화
    INSERT INTO statedb.user_progression (user_id, rank_code, experience_points, level)
    VALUES (NEW.user_id, 'novice', 0, 1);

    -- user_equipment 초기화
    INSERT INTO statedb.user_equipment (user_id, sword_status, uniform_status, crow_status)
    VALUES (NEW.user_id, 'good', 'worn', 'waiting');

    -- 초기 XP 거래 기록
    INSERT INTO statedb.xp_transactions (user_id, xp_amount, xp_type, xp_balance_after, level_before, level_after, description)
    VALUES (NEW.user_id, 0, 'event', 0, 1, 1, '귀살대 입문 - 견습생 계급 부여');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
DROP TRIGGER IF EXISTS trigger_create_user_progression ON statedb.users;
CREATE TRIGGER trigger_create_user_progression
    AFTER INSERT ON statedb.users
    FOR EACH ROW
    EXECUTE FUNCTION create_user_progression();

COMMENT ON FUNCTION create_user_progression() IS '신규 사용자 생성 시 progression 및 equipment 자동 초기화';

-- ============================================================
-- 6. 기존 사용자 초기화
-- ============================================================

-- 기존 사용자 중 progression 데이터가 없는 경우 초기화
INSERT INTO statedb.user_progression (user_id, rank_code, experience_points, level)
SELECT user_id, 'novice', 0, 1
FROM statedb.users
WHERE user_id NOT IN (SELECT user_id FROM statedb.user_progression)
ON CONFLICT (user_id) DO NOTHING;

-- 기존 사용자 중 equipment 데이터가 없는 경우 초기화
INSERT INTO statedb.user_equipment (user_id, sword_status, uniform_status, crow_status)
SELECT user_id, 'good', 'worn', 'waiting'
FROM statedb.users
WHERE user_id NOT IN (SELECT user_id FROM statedb.user_equipment)
ON CONFLICT (user_id) DO NOTHING;

-- 기존 사용자에게 초기 XP 거래 기록 추가 (기록이 없는 경우만)
INSERT INTO statedb.xp_transactions (user_id, xp_amount, xp_type, xp_balance_after, level_before, level_after, description)
SELECT user_id, 0, 'event', 0, 1, 1, '기존 사용자 - Progression 시스템 초기화'
FROM statedb.users
WHERE user_id NOT IN (SELECT DISTINCT user_id FROM statedb.xp_transactions);

-- ============================================================
-- 7. 유틸리티 뷰 (Views)
-- ============================================================

-- 사용자 전체 진행도 요약 뷰
CREATE OR REPLACE VIEW statedb.v_user_progression_summary AS
SELECT
    up.user_id,
    u.username,
    u.display_name,
    up.rank_code,
    rd.rank_name_ko,
    rd.icon_emoji AS rank_icon,
    up.experience_points,
    up.level,
    rd.min_xp AS current_rank_min_xp,
    (SELECT min_xp FROM statedb.rank_definitions WHERE min_xp > up.experience_points ORDER BY min_xp LIMIT 1) AS next_rank_xp,
    up.total_messages,
    up.total_sessions,
    up.total_play_minutes,
    up.scenarios_completed,
    up.achievements_count,
    ue.sword_status,
    ue.uniform_status,
    ue.crow_status,
    up.updated_at
FROM statedb.user_progression up
LEFT JOIN statedb.users u ON up.user_id = u.user_id
LEFT JOIN statedb.rank_definitions rd ON
    up.experience_points >= rd.min_xp AND
    up.level BETWEEN rd.level_range_start AND rd.level_range_end
LEFT JOIN statedb.user_equipment ue ON up.user_id = ue.user_id;

COMMENT ON VIEW statedb.v_user_progression_summary IS '사용자 진행도 전체 요약 (rank + equipment + stats)';

-- ============================================================
-- 완료 메시지
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 012_user_progression.sql 완료';
    RAISE NOTICE '📊 생성된 테이블:';
    RAISE NOTICE '  - rank_definitions (계급 정의) - 5개 계급';
    RAISE NOTICE '  - user_progression (사용자 진행도)';
    RAISE NOTICE '  - user_equipment (사용자 장비)';
    RAISE NOTICE '  - xp_transactions (경험치 거래 내역)';
    RAISE NOTICE '🔄 트리거: 신규 사용자 자동 초기화';
    RAISE NOTICE '👥 기존 사용자 %개 초기화 완료', (SELECT COUNT(*) FROM statedb.user_progression);
END $$;
