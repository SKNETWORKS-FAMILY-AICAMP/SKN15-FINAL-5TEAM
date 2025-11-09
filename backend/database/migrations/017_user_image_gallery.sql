-- ============================================================
-- Migration 017: User Image Gallery System
-- Description: 사용자별 이미지 획득 기록 및 갤러리 시스템
-- Author: Claude Code
-- Date: 2025-01-09
-- ============================================================

-- ============================================================
-- Table: user_unlocked_images (사용자별 획득한 이미지)
-- ============================================================
CREATE TABLE IF NOT EXISTS statedb.user_unlocked_images (
    unlock_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 사용자 및 이미지 정보
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES statedb.image_assets(image_id) ON DELETE CASCADE,

    -- 획득 정보
    unlocked_at TIMESTAMP DEFAULT NOW(),
    scenario_id VARCHAR(50),
    session_id UUID,
    stage_id VARCHAR(100),

    -- 메타데이터
    unlock_method VARCHAR(50) DEFAULT 'story_progress', -- story_progress, manual, reward 등

    UNIQUE (user_id, image_id)
);

CREATE INDEX idx_user_unlocked_user ON statedb.user_unlocked_images(user_id);
CREATE INDEX idx_user_unlocked_image ON statedb.user_unlocked_images(image_id);
CREATE INDEX idx_user_unlocked_time ON statedb.user_unlocked_images(user_id, unlocked_at DESC);

-- ============================================================
-- Function: get_user_unlocked_images (사용자 획득 이미지 조회)
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.get_user_unlocked_images(
    p_user_id UUID,
    p_scenario_id VARCHAR(50) DEFAULT NULL
)
RETURNS TABLE(
    image_id UUID,
    image_path VARCHAR,
    image_name VARCHAR,
    image_type VARCHAR,
    index_number INT,
    description TEXT,
    tags TEXT[],
    unlocked_at TIMESTAMP,
    scenario_id VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ia.image_id,
        ia.image_path,
        ia.image_name,
        ia.image_type,
        ia.index_number,
        ia.description,
        ia.tags,
        uui.unlocked_at,
        ia.scenario_id
    FROM statedb.user_unlocked_images uui
    JOIN statedb.image_assets ia ON uui.image_id = ia.image_id
    WHERE uui.user_id = p_user_id
        AND (p_scenario_id IS NULL OR ia.scenario_id = p_scenario_id)
        AND ia.is_active = true
    ORDER BY uui.unlocked_at DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Function: get_all_images_with_unlock_status (모든 이미지 + 획득 상태)
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.get_all_images_with_unlock_status(
    p_user_id UUID,
    p_scenario_id VARCHAR(50) DEFAULT NULL
)
RETURNS TABLE(
    image_id UUID,
    image_path VARCHAR,
    image_name VARCHAR,
    image_type VARCHAR,
    index_number INT,
    description TEXT,
    tags TEXT[],
    scenario_id VARCHAR,
    is_unlocked BOOLEAN,
    unlocked_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ia.image_id,
        ia.image_path,
        ia.image_name,
        ia.image_type,
        ia.index_number,
        ia.description,
        ia.tags,
        ia.scenario_id,
        (uui.unlock_id IS NOT NULL) as is_unlocked,
        uui.unlocked_at
    FROM statedb.image_assets ia
    LEFT JOIN statedb.user_unlocked_images uui
        ON ia.image_id = uui.image_id AND uui.user_id = p_user_id
    WHERE ia.is_active = true
        AND (p_scenario_id IS NULL OR ia.scenario_id = p_scenario_id)
    ORDER BY ia.scenario_id, ia.index_number;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Function: unlock_image_for_user (이미지 획득 처리)
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.unlock_image_for_user(
    p_user_id UUID,
    p_image_id UUID,
    p_scenario_id VARCHAR(50) DEFAULT NULL,
    p_session_id UUID DEFAULT NULL,
    p_stage_id VARCHAR(100) DEFAULT NULL,
    p_unlock_method VARCHAR(50) DEFAULT 'story_progress'
)
RETURNS BOOLEAN AS $$
DECLARE
    v_already_unlocked BOOLEAN;
BEGIN
    -- 이미 획득했는지 확인
    SELECT EXISTS(
        SELECT 1 FROM statedb.user_unlocked_images
        WHERE user_id = p_user_id AND image_id = p_image_id
    ) INTO v_already_unlocked;

    -- 이미 획득한 경우 false 반환
    IF v_already_unlocked THEN
        RETURN FALSE;
    END IF;

    -- 새로 획득
    INSERT INTO statedb.user_unlocked_images (
        user_id,
        image_id,
        scenario_id,
        session_id,
        stage_id,
        unlock_method
    ) VALUES (
        p_user_id,
        p_image_id,
        p_scenario_id,
        p_session_id,
        p_stage_id,
        p_unlock_method
    );

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Function: get_user_gallery_stats (사용자 갤러리 통계)
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.get_user_gallery_stats(
    p_user_id UUID,
    p_scenario_id VARCHAR(50) DEFAULT NULL
)
RETURNS TABLE(
    total_images INT,
    unlocked_images INT,
    unlock_percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INT as total_images,
        COUNT(uui.unlock_id)::INT as unlocked_images,
        ROUND(
            (COUNT(uui.unlock_id)::NUMERIC / NULLIF(COUNT(*)::NUMERIC, 0)) * 100,
            2
        ) as unlock_percentage
    FROM statedb.image_assets ia
    LEFT JOIN statedb.user_unlocked_images uui
        ON ia.image_id = uui.image_id AND uui.user_id = p_user_id
    WHERE ia.is_active = true
        AND (p_scenario_id IS NULL OR ia.scenario_id = p_scenario_id);
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 권한 설정
-- ============================================================
GRANT SELECT, INSERT ON statedb.user_unlocked_images TO statedb_app;
GRANT EXECUTE ON FUNCTION statedb.get_user_unlocked_images TO statedb_app;
GRANT EXECUTE ON FUNCTION statedb.get_all_images_with_unlock_status TO statedb_app;
GRANT EXECUTE ON FUNCTION statedb.unlock_image_for_user TO statedb_app;
GRANT EXECUTE ON FUNCTION statedb.get_user_gallery_stats TO statedb_app;

-- ============================================================
-- 마이그레이션 완료 확인
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 017 completed successfully';
    RAISE NOTICE '  - Created table: user_unlocked_images';
    RAISE NOTICE '  - Created 4 functions for gallery management';
END $$;
