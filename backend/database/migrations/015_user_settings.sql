-- ============================================================
-- Migration 015: User Settings Table
-- ============================================================
-- 사용자별 설정 정보를 저장하는 테이블
-- - 사운드 설정 (BGM, 효과음)
-- - UI 설정 (언어, 폰트, 애니메이션 속도)
-- - 게임 설정 (자동 저장)
-- ============================================================

-- ============================================================
-- 1. user_settings 테이블 생성
-- ============================================================
CREATE TABLE IF NOT EXISTS statedb.user_settings (
    user_id UUID PRIMARY KEY REFERENCES statedb.users(user_id) ON DELETE CASCADE,

    -- Sound settings
    sound_enabled BOOLEAN DEFAULT true,
    bgm_volume INTEGER DEFAULT 70 CHECK (bgm_volume >= 0 AND bgm_volume <= 100),
    sfx_volume INTEGER DEFAULT 80 CHECK (sfx_volume >= 0 AND sfx_volume <= 100),

    -- Game settings
    auto_save BOOLEAN DEFAULT true,
    language VARCHAR(10) DEFAULT 'ko',
    font_size VARCHAR(20) DEFAULT 'medium' CHECK (font_size IN ('small', 'medium', 'large')),
    animation_speed VARCHAR(20) DEFAULT 'normal' CHECK (animation_speed IN ('slow', 'normal', 'fast')),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON statedb.user_settings(user_id);

-- ============================================================
-- 2. updated_at 자동 업데이트 트리거
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.update_user_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_settings_timestamp ON statedb.user_settings;
CREATE TRIGGER trigger_update_user_settings_timestamp
    BEFORE UPDATE ON statedb.user_settings
    FOR EACH ROW
    EXECUTE FUNCTION statedb.update_user_settings_timestamp();

-- ============================================================
-- 3. 신규 사용자 생성 시 기본 설정 자동 생성 트리거
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.create_default_user_settings()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO statedb.user_settings (user_id)
    VALUES (NEW.user_id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_create_default_user_settings ON statedb.users;
CREATE TRIGGER trigger_create_default_user_settings
    AFTER INSERT ON statedb.users
    FOR EACH ROW
    EXECUTE FUNCTION statedb.create_default_user_settings();

-- ============================================================
-- 4. 기존 사용자에게 기본 설정 추가 (마이그레이션)
-- ============================================================
INSERT INTO statedb.user_settings (user_id)
SELECT user_id
FROM statedb.users
WHERE user_id NOT IN (SELECT user_id FROM statedb.user_settings)
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================
-- 마이그레이션 완료
-- ============================================================
-- 확인 쿼리:
-- SELECT * FROM statedb.user_settings LIMIT 10;
-- SELECT COUNT(*) FROM statedb.user_settings;
