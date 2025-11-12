--
-- User Settings Table
-- 사용자 설정 정보 (볼륨, 언어 등)
--

-- 스키마 이전: 기존 public.user_settings 제거
DROP TABLE IF EXISTS public.user_settings CASCADE;

CREATE TABLE IF NOT EXISTS auth.user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(user_id) ON DELETE CASCADE,

    -- Sound Settings
    sound_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    bgm_volume INTEGER NOT NULL DEFAULT 80 CHECK (bgm_volume >= 0 AND bgm_volume <= 100),
    sfx_volume INTEGER NOT NULL DEFAULT 100 CHECK (sfx_volume >= 0 AND sfx_volume <= 100),

    -- Language Settings
    language VARCHAR(10) NOT NULL DEFAULT 'ko',

    -- Timestamps
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON auth.user_settings(user_id);

-- Comments
COMMENT ON TABLE auth.user_settings IS '사용자 설정 정보 (볼륨, 언어 등)';
COMMENT ON COLUMN auth.user_settings.user_id IS '사용자 ID (FK to auth.users)';
COMMENT ON COLUMN auth.user_settings.sound_enabled IS '사운드 활성화 여부';
COMMENT ON COLUMN auth.user_settings.bgm_volume IS 'BGM 볼륨 (0-100)';
COMMENT ON COLUMN auth.user_settings.sfx_volume IS 'SFX 볼륨 (0-100)';
COMMENT ON COLUMN auth.user_settings.language IS '언어 설정 (ko/en/ja)';
COMMENT ON COLUMN auth.user_settings.updated_at IS '최종 수정 시간';
