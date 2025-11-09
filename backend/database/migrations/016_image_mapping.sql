-- ============================================================
-- Migration 016: Image Mapping System
-- Description: DB 기반 이미지 매핑 시스템 구축
-- Author: Claude Code
-- Date: 2025-01-09
-- ============================================================

-- ============================================================
-- Table 1: image_assets (이미지 자산 메타데이터)
-- ============================================================
CREATE TABLE IF NOT EXISTS statedb.image_assets (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 이미지 정보
    image_path VARCHAR(500) NOT NULL UNIQUE,
    image_name VARCHAR(255) NOT NULL,
    image_type VARCHAR(50) DEFAULT 'cutscene',

    -- 메타데이터
    scenario_id VARCHAR(50) REFERENCES statedb.scenarios(scenario_id) ON DELETE CASCADE,
    index_number INT,
    description TEXT,
    tags TEXT[],

    -- 상태 관리
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_image_assets_scenario ON statedb.image_assets(scenario_id) WHERE is_active = true;
CREATE INDEX idx_image_assets_index ON statedb.image_assets(scenario_id, index_number);

-- ============================================================
-- Table 2: scenario_stage_images (시나리오별 스테이지 이미지)
-- ============================================================
CREATE TABLE IF NOT EXISTS statedb.scenario_stage_images (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    scenario_id VARCHAR(50) NOT NULL REFERENCES statedb.scenarios(scenario_id) ON DELETE CASCADE,
    stage_id VARCHAR(100) NOT NULL,

    -- 기본 이미지
    default_image_id UUID REFERENCES statedb.image_assets(image_id) ON DELETE SET NULL,

    stage_order INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (scenario_id, stage_id)
);

CREATE INDEX idx_stage_images_scenario ON statedb.scenario_stage_images(scenario_id);

-- ============================================================
-- Table 3: image_mapping_rules (조건부 이미지 매핑 규칙)
-- ============================================================
CREATE TABLE IF NOT EXISTS statedb.image_mapping_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    mapping_id UUID NOT NULL REFERENCES statedb.scenario_stage_images(mapping_id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES statedb.image_assets(image_id) ON DELETE CASCADE,

    -- 우선순위 (높을수록 먼저 평가)
    priority INT DEFAULT 50,

    -- 범위 조건
    turn_min INT DEFAULT 0,
    turn_max INT DEFAULT 999,
    dialogue_count_min INT DEFAULT 0,
    dialogue_count_max INT DEFAULT 999,

    -- 조건부 매칭
    required_flags TEXT[],
    excluded_flags TEXT[],

    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mapping_rules_priority ON statedb.image_mapping_rules(mapping_id, priority DESC) WHERE is_active = true;
CREATE INDEX idx_mapping_rules_flags ON statedb.image_mapping_rules USING GIN(required_flags) WHERE required_flags IS NOT NULL;

-- ============================================================
-- Table 4: scenario_default_images (시나리오 전체 기본 이미지)
-- ============================================================
CREATE TABLE IF NOT EXISTS statedb.scenario_default_images (
    scenario_id VARCHAR(50) PRIMARY KEY REFERENCES statedb.scenarios(scenario_id) ON DELETE CASCADE,
    default_image_id UUID REFERENCES statedb.image_assets(image_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- Function: get_best_image_for_stage (최적 이미지 선택)
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.get_best_image_for_stage(
    p_scenario_id VARCHAR(50),
    p_stage_id VARCHAR(100),
    p_turn_count INT DEFAULT 0,
    p_dialogue_count INT DEFAULT 0,
    p_event_flags TEXT[] DEFAULT ARRAY[]::TEXT[]
)
RETURNS TABLE(
    image_id UUID,
    image_path VARCHAR,
    image_name VARCHAR,
    index_number INT,
    priority INT,
    description TEXT
) AS $$
BEGIN
    -- 우선순위 높은 매핑 규칙부터 매칭
    RETURN QUERY
    SELECT
        ia.image_id,
        ia.image_path,
        ia.image_name,
        ia.index_number,
        imr.priority,
        COALESCE(imr.description, ia.description) as description
    FROM statedb.image_mapping_rules imr
    JOIN statedb.image_assets ia ON imr.image_id = ia.image_id
    JOIN statedb.scenario_stage_images ssa ON imr.mapping_id = ssa.mapping_id
    WHERE
        ssa.scenario_id = p_scenario_id
        AND ssa.stage_id = p_stage_id
        AND imr.is_active = true
        AND p_turn_count BETWEEN imr.turn_min AND imr.turn_max
        AND p_dialogue_count BETWEEN imr.dialogue_count_min AND imr.dialogue_count_max
        AND (imr.required_flags IS NULL OR imr.required_flags <@ p_event_flags)
        AND (imr.excluded_flags IS NULL OR NOT (imr.excluded_flags && p_event_flags))
    ORDER BY imr.priority DESC
    LIMIT 1;

    -- Fallback 1: 스테이지 기본 이미지
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT
            ia.image_id,
            ia.image_path,
            ia.image_name,
            ia.index_number,
            0::INT as priority,
            'Stage default image' as description
        FROM statedb.scenario_stage_images ssa
        JOIN statedb.image_assets ia ON ssa.default_image_id = ia.image_id
        WHERE ssa.scenario_id = p_scenario_id AND ssa.stage_id = p_stage_id;
    END IF;

    -- Fallback 2: 시나리오 기본 이미지
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT
            ia.image_id,
            ia.image_path,
            ia.image_name,
            ia.index_number,
            0::INT as priority,
            'Scenario default image' as description
        FROM statedb.scenario_default_images sdi
        JOIN statedb.image_assets ia ON sdi.default_image_id = ia.image_id
        WHERE sdi.scenario_id = p_scenario_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 초기 데이터: cutscene5_llm_driven 시나리오 이미지 등록
-- ============================================================

-- 이미지 자산 등록 (인덱스 1-21)
INSERT INTO statedb.image_assets (image_path, image_name, scenario_id, index_number, description, tags)
VALUES
    ('1', '무한열차 기본 배경', 'cutscene5_llm_driven', 1, '무한열차 내부 기본 장면', ARRAY['train', 'interior']),
    ('2', '무한열차 객차', 'cutscene5_llm_driven', 2, '객차 내부', ARRAY['train', 'cabin']),
    ('3', '렌고쿠 등장', 'cutscene5_llm_driven', 3, '렌고쿠 쿄쥬로 등장', ARRAY['rengoku', 'character']),
    ('4', '대화 장면', 'cutscene5_llm_driven', 4, '캐릭터들의 대화', ARRAY['conversation']),
    ('5', '긴장감 고조', 'cutscene5_llm_driven', 5, '위기 상황', ARRAY['tension']),
    ('6', '아카자 등장', 'cutscene5_llm_driven', 6, '아카자 등장 장면', ARRAY['akaza', 'villain']),
    ('7', '전투 준비', 'cutscene5_llm_driven', 7, '전투 준비 장면', ARRAY['battle', 'prepare']),
    ('8', '캐릭터 모집', 'cutscene5_llm_driven', 8, '동료 모집 장면', ARRAY['recruit', 'team']),
    ('9', '이노스케 합류', 'cutscene5_llm_driven', 9, '이노스케 등장', ARRAY['inosuke', 'recruit']),
    ('10', '젠이츠 합류', 'cutscene5_llm_driven', 10, '젠이츠 등장', ARRAY['zenitsu', 'recruit']),
    ('11', '네즈코 등장', 'cutscene5_llm_driven', 11, '네즈코 등장', ARRAY['nezuko', 'character']),
    ('12', '전투 시작', 'cutscene5_llm_driven', 12, '전투 시작 장면', ARRAY['battle', 'start']),
    ('13', '렌고쿠의 희생', 'cutscene5_llm_driven', 13, '렌고쿠 희생 장면', ARRAY['rengoku', 'sacrifice', 'emotional']),
    ('14', '슬픔', 'cutscene5_llm_driven', 14, '슬픔 장면', ARRAY['emotional', 'sad']),
    ('15', '결의', 'cutscene5_llm_driven', 15, '결의의 순간', ARRAY['determination']),
    ('16', '전투 종료', 'cutscene5_llm_driven', 16, '전투 종료 장면', ARRAY['battle', 'end']),
    ('17', '여파', 'cutscene5_llm_driven', 17, '전투 이후', ARRAY['aftermath']),
    ('18', '치유', 'cutscene5_llm_driven', 18, '회복 장면', ARRAY['healing']),
    ('19', '희망', 'cutscene5_llm_driven', 19, '희망 장면', ARRAY['hope']),
    ('20', '엔딩 준비', 'cutscene5_llm_driven', 20, '엔딩 전 장면', ARRAY['ending']),
    ('21', '엔딩', 'cutscene5_llm_driven', 21, '최종 엔딩 장면', ARRAY['ending', 'final'])
ON CONFLICT (image_path) DO NOTHING;

-- 시나리오 기본 이미지 설정
INSERT INTO statedb.scenario_default_images (scenario_id, default_image_id)
SELECT 'cutscene5_llm_driven', image_id
FROM statedb.image_assets
WHERE scenario_id = 'cutscene5_llm_driven' AND index_number = 1
ON CONFLICT (scenario_id) DO NOTHING;

-- 스테이지별 기본 이미지 설정
INSERT INTO statedb.scenario_stage_images (scenario_id, stage_id, default_image_id, stage_order, description)
SELECT
    'cutscene5_llm_driven',
    stage_id,
    (SELECT image_id FROM statedb.image_assets WHERE scenario_id = 'cutscene5_llm_driven' AND index_number = default_index),
    stage_order,
    description
FROM (VALUES
    ('INTRO', 1, 1, '도입부 - 무한열차'),
    ('HEROES_ARRIVE', 1, 2, '영웅들의 도착'),
    ('ROUTE_CHOICE', 3, 3, '경로 선택'),
    ('RECRUIT', 8, 4, '동료 모집'),
    ('BATTLE', 12, 5, '전투 시작'),
    ('ENDING', 21, 6, '엔딩')
) AS stages(stage_id, default_index, stage_order, description)
ON CONFLICT (scenario_id, stage_id) DO NOTHING;

-- 조건부 매핑 규칙 추가 (INTRO 스테이지 예시)
INSERT INTO statedb.image_mapping_rules (
    mapping_id,
    image_id,
    priority,
    turn_min,
    turn_max,
    dialogue_count_min,
    dialogue_count_max,
    description
)
SELECT
    ssa.mapping_id,
    ia.image_id,
    rules.priority,
    rules.turn_min,
    rules.turn_max,
    rules.dialogue_min,
    rules.dialogue_max,
    rules.description
FROM (VALUES
    ('INTRO', 1, 100, 0, 999, 0, 5, 'INTRO 초반'),
    ('INTRO', 2, 90, 0, 999, 6, 10, 'INTRO 중반'),
    ('INTRO', 3, 80, 0, 999, 11, 999, 'INTRO 후반'),
    ('HEROES_ARRIVE', 2, 100, 0, 999, 0, 3, 'HEROES_ARRIVE 초반'),
    ('HEROES_ARRIVE', 3, 90, 0, 999, 4, 999, 'HEROES_ARRIVE 중후반'),
    ('ROUTE_CHOICE', 3, 100, 0, 999, 0, 999, 'ROUTE_CHOICE'),
    ('RECRUIT', 8, 100, 0, 999, 0, 5, 'RECRUIT 기본'),
    ('RECRUIT', 9, 90, 0, 999, 6, 999, 'RECRUIT 진행'),
    ('BATTLE', 12, 100, 0, 999, 0, 10, 'BATTLE 초반'),
    ('BATTLE', 13, 90, 0, 999, 11, 999, 'BATTLE 격렬'),
    ('ENDING', 21, 100, 0, 999, 0, 999, 'ENDING')
) AS rules(stage_id, image_index, priority, turn_min, turn_max, dialogue_min, dialogue_max, description)
JOIN statedb.scenario_stage_images ssa ON ssa.scenario_id = 'cutscene5_llm_driven' AND ssa.stage_id = rules.stage_id
JOIN statedb.image_assets ia ON ia.scenario_id = 'cutscene5_llm_driven' AND ia.index_number = rules.image_index
ON CONFLICT DO NOTHING;

-- ============================================================
-- 권한 설정
-- ============================================================
GRANT SELECT, INSERT, UPDATE ON statedb.image_assets TO statedb_app;
GRANT SELECT, INSERT, UPDATE ON statedb.scenario_stage_images TO statedb_app;
GRANT SELECT, INSERT, UPDATE ON statedb.image_mapping_rules TO statedb_app;
GRANT SELECT, INSERT, UPDATE ON statedb.scenario_default_images TO statedb_app;
GRANT EXECUTE ON FUNCTION statedb.get_best_image_for_stage TO statedb_app;

-- ============================================================
-- 마이그레이션 완료 확인
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 016 completed successfully';
    RAISE NOTICE '  - Created 4 tables: image_assets, scenario_stage_images, image_mapping_rules, scenario_default_images';
    RAISE NOTICE '  - Created function: get_best_image_for_stage()';
    RAISE NOTICE '  - Inserted % images', (SELECT COUNT(*) FROM statedb.image_assets WHERE scenario_id = 'cutscene5_llm_driven');
    RAISE NOTICE '  - Inserted % stage mappings', (SELECT COUNT(*) FROM statedb.scenario_stage_images WHERE scenario_id = 'cutscene5_llm_driven');
    RAISE NOTICE '  - Inserted % mapping rules', (SELECT COUNT(*) FROM statedb.image_mapping_rules);
END $$;
