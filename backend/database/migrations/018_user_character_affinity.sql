-- ============================================================
-- 018_user_character_affinity.sql
-- 사용자별 캐릭터 글로벌 친밀도 시스템
-- ============================================================
-- 목적: 모든 세션을 통틀어 사용자-캐릭터 간 누적 친밀도 관리
-- 최대 1000점, 레벨 시스템 포함
-- ============================================================

-- 1. 글로벌 캐릭터 친밀도 테이블
CREATE TABLE IF NOT EXISTS statedb.user_character_affinity (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    character_name VARCHAR(255) NOT NULL,

    -- 친밀도 점수 (최대 1000점)
    total_affinity_score INTEGER NOT NULL DEFAULT 0 CHECK (total_affinity_score >= 0 AND total_affinity_score <= 1000),

    -- 친밀도 레벨 (100점당 1레벨, 최대 10레벨)
    affinity_level INTEGER NOT NULL DEFAULT 1 CHECK (affinity_level >= 1 AND affinity_level <= 10),

    -- 통계 정보
    total_interactions INTEGER NOT NULL DEFAULT 0,
    last_interaction_at TIMESTAMP DEFAULT NOW(),

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 유니크 제약: 사용자당 캐릭터 하나만
    UNIQUE(user_id, character_name)
);

-- 2. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_user_character_affinity_user
    ON statedb.user_character_affinity(user_id);

CREATE INDEX IF NOT EXISTS idx_user_character_affinity_score
    ON statedb.user_character_affinity(user_id, total_affinity_score DESC);

CREATE INDEX IF NOT EXISTS idx_user_character_affinity_character
    ON statedb.user_character_affinity(character_name);

-- 3. 친밀도 레벨 자동 계산 함수
CREATE OR REPLACE FUNCTION statedb.calculate_affinity_level(score INTEGER)
RETURNS INTEGER AS $$
BEGIN
    -- 100점당 1레벨 (1~10레벨)
    RETURN LEAST(10, GREATEST(1, (score / 100) + 1));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 4. 친밀도 업데이트 시 레벨 자동 계산 트리거
CREATE OR REPLACE FUNCTION statedb.update_affinity_level()
RETURNS TRIGGER AS $$
BEGIN
    NEW.affinity_level := statedb.calculate_affinity_level(NEW.total_affinity_score);
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_affinity_level ON statedb.user_character_affinity;
CREATE TRIGGER trigger_update_affinity_level
    BEFORE INSERT OR UPDATE OF total_affinity_score
    ON statedb.user_character_affinity
    FOR EACH ROW
    EXECUTE FUNCTION statedb.update_affinity_level();

-- 5. 친밀도 업데이트/삽입 함수 (UPSERT)
CREATE OR REPLACE FUNCTION statedb.upsert_character_affinity(
    p_user_id UUID,
    p_character_name VARCHAR(255),
    p_affinity_change INTEGER
)
RETURNS TABLE(
    character_name VARCHAR(255),
    total_affinity_score INTEGER,
    affinity_level INTEGER,
    score_change INTEGER
) AS $$
DECLARE
    v_old_score INTEGER := 0;
    v_new_score INTEGER;
BEGIN
    -- 기존 점수 조회
    SELECT uca.total_affinity_score INTO v_old_score
    FROM statedb.user_character_affinity uca
    WHERE uca.user_id = p_user_id AND uca.character_name = p_character_name;

    -- 새 점수 계산 (0~1000 범위 제한)
    v_new_score := GREATEST(0, LEAST(1000, COALESCE(v_old_score, 0) + p_affinity_change));

    -- UPSERT
    INSERT INTO statedb.user_character_affinity (
        user_id,
        character_name,
        total_affinity_score,
        total_interactions,
        last_interaction_at
    )
    VALUES (
        p_user_id,
        p_character_name,
        v_new_score,
        1,
        NOW()
    )
    ON CONFLICT (user_id, character_name)
    DO UPDATE SET
        total_affinity_score = v_new_score,
        total_interactions = statedb.user_character_affinity.total_interactions + 1,
        last_interaction_at = NOW(),
        updated_at = NOW();

    -- 결과 반환
    RETURN QUERY
    SELECT
        uca.character_name,
        uca.total_affinity_score,
        uca.affinity_level,
        p_affinity_change as score_change
    FROM statedb.user_character_affinity uca
    WHERE uca.user_id = p_user_id AND uca.character_name = p_character_name;
END;
$$ LANGUAGE plpgsql;

-- 6. 사용자별 TOP N 캐릭터 조회 함수
CREATE OR REPLACE FUNCTION statedb.get_top_affinity_characters(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    character_name VARCHAR(255),
    total_affinity_score INTEGER,
    affinity_level INTEGER,
    total_interactions INTEGER,
    last_interaction_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        uca.character_name,
        uca.total_affinity_score,
        uca.affinity_level,
        uca.total_interactions,
        uca.last_interaction_at
    FROM statedb.user_character_affinity uca
    WHERE uca.user_id = p_user_id
    ORDER BY uca.total_affinity_score DESC, uca.last_interaction_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 7. 코멘트
COMMENT ON TABLE statedb.user_character_affinity IS '사용자별 캐릭터 글로벌 친밀도 (최대 1000점, 레벨 시스템)';
COMMENT ON COLUMN statedb.user_character_affinity.total_affinity_score IS '누적 친밀도 점수 (0~1000)';
COMMENT ON COLUMN statedb.user_character_affinity.affinity_level IS '친밀도 레벨 (1~10, 100점당 1레벨)';
COMMENT ON FUNCTION statedb.upsert_character_affinity IS '캐릭터 친밀도 업데이트 (없으면 생성)';
COMMENT ON FUNCTION statedb.get_top_affinity_characters IS '사용자의 친밀도 상위 캐릭터 조회';
